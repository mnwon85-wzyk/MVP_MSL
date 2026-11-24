import torch
import torch.nn as nn


class AttnPool(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.w = nn.Linear(d, 1)

    def forward(self, h, return_alpha=False):
        alpha = torch.softmax(
            self.w(h).squeeze(-1),
            dim=1
        )
        ctx = (alpha.unsqueeze(-1) * h).sum(dim=1)

        return (ctx, alpha) if return_alpha else ctx


class ECGNet(nn.Module):
    def __init__(self, n_cls=3, hidden=64, n_rr=4):
        super().__init__()

        self.stem = nn.Sequential(
            nn.Conv1d(1, 16, kernel_size=7, padding=3),
            nn.BatchNorm1d(16),
            nn.ReLU(),

            nn.Conv1d(
                16,
                32,
                kernel_size=7,
                padding=3,
                stride=2
            ),
            nn.BatchNorm1d(32),
            nn.ReLU()
        )

        self.lstm = nn.LSTM(
            input_size=32,
            hidden_size=hidden,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=0.2
        )

        self.attn = AttnPool(2 * hidden)

        self.rr = nn.Sequential(
            nn.Linear(n_rr, 16),
            nn.ReLU()
        )

        self.head = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(2 * hidden + 16, n_cls)
        )

    def forward(self, x, rr, return_alpha=False):
        h = self.stem(x.unsqueeze(1))
        print("stem     ", tuple(h.shape))

        h = h.transpose(1, 2)
        print("transpose", tuple(h.shape))

        h, _ = self.lstm(h)
        print("lstm     ", tuple(h.shape))

        ctx, alpha = self.attn(h, return_alpha=True)
        print("attn     ", tuple(ctx.shape), tuple(alpha.shape))

        rr_features = self.rr(rr)
        z = torch.cat([ctx, rr_features], dim=1)
        print("concat   ", tuple(z.shape))

        out = self.head(z)

        return (out, alpha) if return_alpha else out


# 모델 생성
m = ECGNet()

# 임의 입력으로 테스트
out, alpha = m(
    torch.randn(8, 252),
    torch.randn(8, 4),
    return_alpha=True
)

print("output shape:", tuple(out.shape))
print("alpha sum:", alpha.sum(dim=1))  # 모두 1.0


# 모듈별 파라미터 수 출력
for name, mod in [
    ("stem", m.stem),
    ("lstm", m.lstm),
    ("attn", m.attn),
    ("rr", m.rr),
    ("head", m.head)
]:
    parameter_count = sum(
        p.numel() for p in mod.parameters()
    )
    print(f"{name:5s} {parameter_count:>8,}")

print(
    "total",
    sum(p.numel() for p in m.parameters())
)

import copy

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn

from sklearn.metrics import f1_score
from torch.utils.data import (
    DataLoader,
    Dataset,
    WeightedRandomSampler
)


CLS = {
    "N": 0,
    "S": 1,
    "V": 2
}


# ---------------------------------------------------------
# 데이터 구성
# ---------------------------------------------------------
def build(recs):
    X = []
    RR = []
    Y = []
    G = []

    for r in recs:
        sig, fs, r_pos, y = load_record(str(r))

        # N, S, V만 남기고 F, Q는 제외
        keep = np.isin(y, list("NSV"))

        xb, rrb, yb = make_beats(
            sig,
            fs,
            r_pos[keep],
            y[keep]
        )

        X.append(xb)
        RR.append(rrb)
        Y.append(yb)
        G += [r] * len(yb)

    return (
        np.concatenate(X),
        np.concatenate(RR),
        np.concatenate(Y),
        np.array(G)
    )


Xtr, RRtr, Ytr, Gtr = build(train_recs)
Xva, RRva, Yva, Gva = build(val_recs)


# ---------------------------------------------------------
# PyTorch Dataset
# ---------------------------------------------------------
class BeatDataset(Dataset):
    def __init__(self, X, RR, Y, augment=False):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.RR = torch.tensor(RR, dtype=torch.float32)

        self.Y = torch.tensor(
            [CLS[c] for c in Y],
            dtype=torch.long
        )

        self.augment = augment

    def __len__(self):
        return len(self.Y)

    def __getitem__(self, i):
        x = self.X[i].clone()

        if self.augment:
            # 진폭을 약 ±10% 범위에서 변경
            amplitude_scale = 1 + 0.2 * (
                torch.rand(1) - 0.5
            )
            x = x * amplitude_scale

            # 가우시안 노이즈 추가
            x = x + 0.03 * torch.randn_like(x)

            # 파형 위치를 좌우로 조금 이동
            shift = int(
                torch.randint(
                    low=-5,
                    high=6,
                    size=(1,)
                ).item()
            )
            x = torch.roll(x, shifts=shift)

        return x, self.RR[i], self.Y[i]


train_ds = BeatDataset(
    Xtr,
    RRtr,
    Ytr,
    augment=True
)

val_ds = BeatDataset(
    Xva,
    RRva,
    Yva,
    augment=False
)


# ---------------------------------------------------------
# 클래스 불균형 보정용 샘플러 및 손실함수
# ---------------------------------------------------------
counts = torch.bincount(
    train_ds.Y,
    minlength=3
).float()

if torch.any(counts == 0):
    raise ValueError(
        f"학습 데이터에 표본이 없는 클래스가 있습니다: "
        f"{counts.tolist()}"
    )

w_cls = (1.0 / counts) ** 0.75

sample_weights = w_cls[train_ds.Y]

sampler = WeightedRandomSampler(
    weights=sample_weights,
    num_samples=len(train_ds),
    replacement=True
)

train_loader = DataLoader(
    train_ds,
    batch_size=256,
    sampler=sampler
)

val_loader = DataLoader(
    val_ds,
    batch_size=512,
    shuffle=False
)

loss_w = (
    counts.sum() / (3 * counts)
).sqrt()

criterion = nn.CrossEntropyLoss(
    weight=loss_w,
    label_smoothing=0.05
)


# ---------------------------------------------------------
# 학습 배치의 클래스 분포 확인
# ---------------------------------------------------------
_, _, yb = next(iter(train_loader))

print(
    "배치 N/S/V:",
    torch.bincount(
        yb,
        minlength=3
    ).tolist()
)


# ---------------------------------------------------------
# 모델 및 학습 설정
# ---------------------------------------------------------
EPOCHS = 30

model = ECGNet()

opt = torch.optim.AdamW(
    model.parameters(),
    lr=2e-3,
    weight_decay=1e-2
)

sched = torch.optim.lr_scheduler.OneCycleLR(
    opt,
    max_lr=2e-3,
    total_steps=EPOCHS * len(train_loader),
    pct_start=0.15
)


# ---------------------------------------------------------
# 검증 함수
# ---------------------------------------------------------
@torch.no_grad()
def evaluate(loader):
    model.eval()

    predictions = []
    targets = []

    for x, rr, y in loader:
        logits = model(x, rr)
        predicted = logits.argmax(dim=1)

        predictions.append(predicted.cpu())
        targets.append(y.cpu())

    predictions = torch.cat(predictions).numpy()
    targets = torch.cat(targets).numpy()

    macro_f1 = f1_score(
        targets,
        predictions,
        average="macro",
        zero_division=0
    )

    class_f1 = f1_score(
        targets,
        predictions,
        labels=[0, 1, 2],
        average=None,
        zero_division=0
    )

    return macro_f1, class_f1


# ---------------------------------------------------------
# 학습 루프
# ---------------------------------------------------------
best = 0.0
best_state = None
patience = 0
hist = []

for epoch in range(EPOCHS):
    model.train()
    running = 0.0

    for x, rr, y in train_loader:
        opt.zero_grad()

        logits = model(x, rr)
        loss = criterion(logits, y)

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0
        )

        opt.step()
        sched.step()

        running += loss.item()

    train_loss = running / len(train_loader)
    macro, per_cls = evaluate(val_loader)

    hist.append(
        (
            train_loss,
            macro,
            per_cls
        )
    )

    print(
        f"ep{epoch:02d} "
        f"loss={train_loss:.3f} "
        f"macroF1={macro:.3f} "
        f"N/S/V={per_cls.round(2)}"
    )

    if macro > best:
        best = macro
        best_state = copy.deepcopy(
            model.state_dict()
        )
        patience = 0

    else:
        patience += 1

    if patience >= 5:
        print("early stop")
        break


# ---------------------------------------------------------
# 최고 성능 모델 저장
# ---------------------------------------------------------
if best_state is None:
    raise RuntimeError(
        "저장할 최적 모델이 없습니다."
    )

model.load_state_dict(best_state)

torch.save(
    best_state,
    "ecgnet_best.pt"
)

print(f"최고 validation macro-F1: {best:.3f}")
print("저장 완료: ecgnet_best.pt")


# ---------------------------------------------------------
# 학습 곡선 출력
# ---------------------------------------------------------
epochs_ran = range(1, len(hist) + 1)
train_losses = [h[0] for h in hist]
valid_macro_f1 = [h[1] for h in hist]

fig, a1 = plt.subplots(
    figsize=(8, 4)
)

a2 = a1.twinx()

a1.plot(
    epochs_ran,
    train_losses,
    color="navy",
    label="train loss"
)

a2.plot(
    epochs_ran,
    valid_macro_f1,
    color="crimson",
    linestyle="--",
    label="valid macro-F1"
)

a1.set_xlabel("epoch")
a1.set_ylabel(
    "train loss",
    color="navy"
)
a2.set_ylabel(
    "validation macro-F1",
    color="crimson"
)

a1.legend(loc="upper left")
a2.legend(loc="upper right")

plt.title("ECGNet Training History")
plt.tight_layout()
plt.show()