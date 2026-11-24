import {
  useEffect,
  useMemo,
  useState,
} from "react";

import "./styles.css";


const API_BASE =
  "http://localhost:8000";

const PATIENT_FETCH_LIMIT =
  100;


const TEXT = {
  kr: {
    home: "홈",
    search: "통합 검색",
    evidenceAnalysis: "근거 분석",
    landscape: "치료 환경",
    listen: "인사이트 수집",
    insightAnalysis: "인사이트 분석",
  },

  en: {
    home: "Home",
    search: "Smart Search",
    evidenceAnalysis: "Evidence Analysis",
    landscape: "Treatment Landscape",
    listen: "Listen",
    insightAnalysis: "Insight Analysis",
  },
};


function safeText(value) {
  if (
    value === null ||
    value === undefined
  ) {
    return "";
  }

  if (
    Array.isArray(value)
  ) {
    return value.join(" · ");
  }

  if (
    typeof value === "object"
  ) {
    try {
      return JSON.stringify(
        value,
        null,
        2
      );
    } catch {
      return String(value);
    }
  }

  return String(value);
}


function itemKey(
  item,
  index = 0
) {
  return (
    `${item?.source || "source"}:` +
    `${
      item?.id ||
      item?.url ||
      item?.title ||
      index
    }`
  );
}


function normalizeSource(
  source
) {
  const value =
    safeText(source)
      .toLowerCase();

  if (
    value.includes("pubmed")
  ) {
    return "pubmed";
  }

  if (
    value.includes(
      "clinical"
    ) ||
    value.includes("trial")
  ) {
    return "trials";
  }

  if (
    value.includes("fda") ||
    value.includes("ema") ||
    value.includes(
      "regulatory"
    )
  ) {
    return "regulatory";
  }

  return "other";
}


function parseFilename(
  disposition,
  fallback
) {
  if (!disposition) {
    return fallback;
  }

  const utfMatch =
    disposition.match(
      /filename\*=UTF-8''([^;]+)/i
    );

  if (utfMatch?.[1]) {
    try {
      return decodeURIComponent(
        utfMatch[1]
      );
    } catch {
      return utfMatch[1];
    }
  }

  const normalMatch =
    disposition.match(
      /filename="?([^";]+)"?/i
    );

  return (
    normalMatch?.[1] ||
    fallback
  );
}


function SidebarItem({
  active,
  icon,
  title,
  subtitle,
  nested = false,
  onClick,
}) {
  return (
    <button
      type="button"
      className={
        [
          "sidebar-item",
          active
            ? "active"
            : "",
          nested
            ? "nested"
            : "",
        ]
          .filter(Boolean)
          .join(" ")
      }
      onClick={onClick}
    >
      <span
        className="sidebar-icon"
      >
        {icon}
      </span>

      <span
        className="sidebar-copy"
      >
        <strong>
          {title}
        </strong>

        {subtitle && (
          <small>
            {subtitle}
          </small>
        )}
      </span>
    </button>
  );
}


function SourceBadge({
  source,
}) {
  return (
    <span
      className="source-badge"
    >
      {safeText(source) ||
        "Source"}
    </span>
  );
}


function HomeSection({
  number,
  eyebrow,
  title,
  subtitle,
  children,
}) {
  const [
    open,
    setOpen,
  ] = useState(false);

  return (
    <section
      className="home-section"
    >
      <div
        className="home-section-header"
      >
        <div
          className="section-number"
        >
          {number}
        </div>

        <div
          className="home-section-heading"
        >
          <span
            className="tiny-label"
          >
            {eyebrow}
          </span>

          <h2>
            {title}
          </h2>

          {subtitle && (
            <p>
              {subtitle}
            </p>
          )}
        </div>

        <button
          type="button"
          className={
            "secondary-button " +
            "compact-button"
          }
          onClick={() =>
            setOpen(
              (value) =>
                !value
            )
          }
        >
          {open
            ? "접기 ▲"
            : "펼치기 ▼"}
        </button>
      </div>

      {open && (
        <div
          className="home-section-content"
        >
          {children}
        </div>
      )}
    </section>
  );
}


function StatusDot({
  name,
  data,
}) {
  const status =
    data?.status ||
    "not-run";

  return (
    <div
      className={
        `live-source ${
          status === "ok"
            ? "ok"
            : status === "error"
            ? "failed"
            : ""
        }`
      }
    >
      <span />

      <div>
        <strong>
          {name}
        </strong>

        <small>
          {data?.refreshed_at
            ? new Date(
                data.refreshed_at
              ).toLocaleTimeString()
            : status}
        </small>
      </div>
    </div>
  );
}


/* =========================================================
   HOME
   ========================================================= */

function HomePage({
  language,
  company,
  setCompany,
  disease,
  setDisease,
  biomarker,
  setBiomarker,
  setting,
  setSetting,
  asset,
  setAsset,
  dashboardData,
  dashboardLoading,
  dashboardError,
  loadDashboard,
  sendPaperToEvidence,
  setPage,
  listenData,
  hcpItems,
}) {
  const data =
    dashboardData || {};

  const fda =
    data.current_treatment_landscape ||
    [];

  const companyPipeline =
    data.company_pipeline ||
    [];

  const competitorPipeline =
    data.competitor_pipeline ||
    [];

  const changes =
    data.what_changed ||
    [];

  const evidence =
    data.latest_scientific_evidence ||
    [];

  const position =
    data.asset_position ||
    {};

  const sourceStatus =
    data.source_status ||
    {};

  return (
    <>
      <header
        className="page-header intelligence-header"
      >
        <span
          className="eyebrow"
        >
          MSL ONE · MEDICAL INTELLIGENCE
        </span>

        <div
          className="intelligence-title-row"
        >
          <div>
            <h1>
              Medical Intelligence Dashboard
            </h1>

            <p>
              {language === "kr"
                ? "오늘 담당 질환에서 무엇을 알아야 하는지 빠르게 확인합니다."
                : "A rapid Medical Affairs view of what matters today."}
            </p>
          </div>

          <div
            className="live-intelligence-badge"
          >
            <span
              className="live-pulse"
            />

            <div>
              <strong>
                LIVE INTELLIGENCE
              </strong>

              <small>
                {data.last_successful_refresh
                  ? (
                      "Last refresh · " +
                      new Date(
                        data.last_successful_refresh
                      ).toLocaleString()
                    )
                  : "Run Refresh Intelligence"}
              </small>
            </div>
          </div>
        </div>
      </header>

      <section
        className="intelligence-query"
      >
        <div
          className="intelligence-query-main"
        >
          <label>
            <span>
              DISEASE / INDICATION
            </span>

            <input
              value={disease}
              placeholder="NSCLC"
              onChange={(event) =>
                setDisease(
                  event.target.value
                )
              }
            />
          </label>

          <label>
            <span>
              BIOMARKER
            </span>

            <input
              value={biomarker}
              placeholder="ROS1"
              onChange={(event) =>
                setBiomarker(
                  event.target.value
                )
              }
            />
          </label>

          <label>
            <span>
              SETTING
            </span>

            <input
              value={setting}
              placeholder="1L"
              onChange={(event) =>
                setSetting(
                  event.target.value
                )
              }
            />
          </label>

          <button
            type="button"
            className="primary-button"
            disabled={
              dashboardLoading ||
              !disease.trim()
            }
            onClick={
              loadDashboard
            }
          >
            {dashboardLoading
              ? "Refreshing..."
              : "↻ Refresh Intelligence"}
          </button>
        </div>

        <div
          className="intelligence-context"
        >
          <label>
            <span>
              MY COMPANY
            </span>

            <select
              value={company}
              onChange={(event) =>
                setCompany(
                  event.target.value
                )
              }
            >
              <option value="GSK">
                GSK
              </option>
            </select>
          </label>

          <label>
            <span>
              MY ASSET
            </span>

            <input
              value={asset}
              placeholder="e.g. Jemperli"
              onChange={(event) =>
                setAsset(
                  event.target.value
                )
              }
            />
          </label>
        </div>
      </section>

      {dashboardError && (
        <div
          className="error"
        >
          {dashboardError}
        </div>
      )}

      {dashboardData && (
        <section
          className="live-source-strip"
        >
          <StatusDot
            name="FDA"
            data={
              sourceStatus.FDA
            }
          />

          <StatusDot
            name="ClinicalTrials.gov"
            data={
              sourceStatus[
                "ClinicalTrials.gov"
              ]
            }
          />

          <StatusDot
            name="PubMed"
            data={
              sourceStatus.PubMed
            }
          />

          <StatusDot
            name="Company source"
            data={
              sourceStatus[
                "Company source"
              ]
            }
          />
        </section>
      )}

      {!dashboardData ? (
        <div
          className="dashboard-start"
        >
          <strong>
            Medical Intelligence
          </strong>

          <p>
            질환을 입력한 뒤
            Refresh Intelligence를
            눌러주세요.
          </p>
        </div>
      ) : (
        <>
          <HomeSection
            number="1"
            eyebrow="CURRENT LANDSCAPE"
            title="FDA-Approved Treatment Landscape"
            subtitle="Disease-based, company-agnostic FDA view."
          >
            {fda.length === 0 ? (
              <div
                className="mini-empty"
              >
                No FDA records returned.
              </div>
            ) : (
              <div
                className="table-wrap"
              >
                <table>
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Generic</th>
                      <th>Manufacturer</th>
                      <th>Application</th>
                      <th>Indication</th>
                    </tr>
                  </thead>

                  <tbody>
                    {fda
                      .slice(0, 20)
                      .map(
                        (
                          item,
                          index
                        ) => (
                          <tr
                            key={
                              item.id ||
                              index
                            }
                          >
                            <td>
                              {item.url ? (
                                <a
                                  href={item.url}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  {item.brand ||
                                    "—"}
                                </a>
                              ) : (
                                item.brand ||
                                "—"
                              )}
                            </td>

                            <td>
                              {item.generic ||
                                "—"}
                            </td>

                            <td>
                              {item.manufacturer ||
                                "—"}
                            </td>

                            <td>
                              {item.application_number ||
                                "—"}
                            </td>

                            <td>
                              {item.indication ||
                                "—"}
                            </td>
                          </tr>
                        )
                      )}
                  </tbody>
                </table>
              </div>
            )}

            <p
              className="section-caution"
            >
              FDA indication match does not
              equal guideline recommendation.
            </p>
          </HomeSection>

          <HomeSection
            number="2"
            eyebrow="MY ASSET POSITION"
            title={
              asset ||
              "Select My Asset"
            }
            subtitle="Cross-trial comparisons cannot establish superiority."
          >
            {!asset ? (
              <div
                className="mini-empty"
              >
                MY ASSET을 입력하세요.
              </div>
            ) : (
              <div
                className="asset-position-grid"
              >
                <article
                  className="my-asset-card"
                >
                  <span
                    className="position-tag"
                  >
                    MY ASSET
                  </span>

                  <h3>
                    {asset}
                  </h3>

                  <p>
                    {position.my_asset?.status ||
                      position.my_asset?.phase ||
                      "Status not established"}
                  </p>
                </article>

                {(position.comparators ||
                  [])
                  .slice(0, 4)
                  .map(
                    (
                      item,
                      index
                    ) => (
                      <article
                        className="comparator-card"
                        key={index}
                      >
                        <span
                          className="position-tag comparator"
                        >
                          COMPARATOR
                        </span>

                        <h3>
                          {item.brand ||
                            item.generic ||
                            "Comparator"}
                        </h3>

                        <p>
                          {item.status ||
                            "—"}
                        </p>
                      </article>
                    )
                  )}
              </div>
            )}

            <div
              className="comparison-warning"
            >
              <strong>
                SCIENTIFIC CAUTION
              </strong>

              <p>
                {position.comparison_note ||
                  "No direct comparative evidence identified."}
              </p>
            </div>
          </HomeSection>

          <HomeSection
            number="3"
            eyebrow="PIPELINE LANDSCAPE"
            title="Clinical Development Landscape"
            subtitle="My Company and competitor pipeline remain separate."
          >
            <div
              className="pipeline-columns"
            >
              <div>
                <div
                  className="pipeline-column-title"
                >
                  <span>
                    MY COMPANY PIPELINE
                  </span>

                  <strong>
                    {companyPipeline.length}
                  </strong>
                </div>

                {companyPipeline.map(
                  (
                    item,
                    index
                  ) => (
                    <a
                      className="trial-intelligence-card company"
                      key={
                        item.id ||
                        index
                      }
                      href={
                        item.url ||
                        "#"
                      }
                      target="_blank"
                      rel="noreferrer"
                    >
                      <strong>
                        {item.asset ||
                          item.title}
                      </strong>

                      <p>
                        {item.target ||
                          safeText(
                            item.interventions
                          )}
                      </p>

                      <small>
                        {item.phase ||
                          item.status}
                      </small>
                    </a>
                  )
                )}
              </div>

              <div>
                <div
                  className="pipeline-column-title"
                >
                  <span>
                    COMPETITOR PIPELINE
                  </span>

                  <strong>
                    {competitorPipeline.length}
                  </strong>
                </div>

                {competitorPipeline
                  .slice(0, 12)
                  .map(
                    (
                      item,
                      index
                    ) => (
                      <a
                        className="trial-intelligence-card"
                        key={
                          item.id ||
                          index
                        }
                        href={
                          item.url ||
                          "#"
                        }
                        target="_blank"
                        rel="noreferrer"
                      >
                        <strong>
                          {item.title ||
                            item.asset}
                        </strong>

                        <p>
                          {safeText(
                            item.interventions
                          )}
                        </p>

                        <small>
                          {item.phase ||
                            item.status}
                        </small>
                      </a>
                    )
                  )}
              </div>
            </div>
          </HomeSection>

          <HomeSection
            number="4"
            eyebrow="WHAT CHANGED?"
            title="Recent Scientific & Development Signals"
            subtitle="Recent FDA, trial and publication signals."
          >
            <div
              className="change-timeline"
            >
              {changes.length === 0 ? (
                <div
                  className="mini-empty"
                >
                  No recent changes returned.
                </div>
              ) : (
                changes.map(
                  (
                    item,
                    index
                  ) => (
                    <article
                      key={index}
                    >
                      <span
                        className="change-type"
                      >
                        {item.type}
                      </span>

                      <div>
                        <strong>
                          {item.title}
                        </strong>

                        <p>
                          {item.detail}
                        </p>

                        <small>
                          {item.date}
                        </small>
                      </div>
                    </article>
                  )
                )
              )}
            </div>
          </HomeSection>

          <HomeSection
            number="5"
            eyebrow="LATEST SCIENTIFIC EVIDENCE"
            title="Recent PubMed Evidence"
            subtitle="Send useful papers directly to the Evidence Basket."
          >
            <div
              className="evidence-dashboard-list"
            >
              {evidence.map(
                (
                  item,
                  index
                ) => (
                  <article
                    key={
                      item.id ||
                      index
                    }
                  >
                    <div
                      className="evidence-dashboard-meta"
                    >
                      <span>
                        {item.journal ||
                          "PubMed"}
                      </span>

                      <small>
                        {item.date}
                      </small>
                    </div>

                    <a
                      href={
                        item.url
                      }
                      target="_blank"
                      rel="noreferrer"
                    >
                      {item.title}
                    </a>

                    <p>
                      {item.abstract}
                    </p>

                    <button
                      type="button"
                      onClick={() =>
                        sendPaperToEvidence(
                          item,
                          index
                        )
                      }
                    >
                      + Evidence Basket
                    </button>
                  </article>
                )
              )}
            </div>
          </HomeSection>

          <HomeSection
            number="6"
            eyebrow="FIELD INTELLIGENCE"
            title="Patient Voice · HCP Insight"
            subtitle="Field signals remain separate from scientific evidence."
          >
            <div
              className="field-intelligence-grid"
            >
              <button
                type="button"
                onClick={() =>
                  setPage("listen")
                }
              >
                <span>
                  PATIENT VOICE
                </span>

                <strong>
                  {listenData?.count ||
                    0}
                </strong>

                <small>
                  signals
                </small>
              </button>

              <button
                type="button"
                onClick={() =>
                  setPage("listen")
                }
              >
                <span>
                  HCP INSIGHT
                </span>

                <strong>
                  {hcpItems.length}
                </strong>

                <small>
                  field insights
                </small>
              </button>

              <button
                type="button"
                onClick={() =>
                  setPage(
                    "listen-analysis"
                  )
                }
              >
                <span>
                  ANALYZE
                </span>

                <strong>
                  →
                </strong>

                <small>
                  Insight Analysis
                </small>
              </button>
            </div>
          </HomeSection>
        </>
      )}
    </>
  );
}


/* =========================================================
   SMART SEARCH
   ========================================================= */

function ResultCard({
  item,
  index,
  selected,
  onToggle,
}) {
  const url =
    item?.url ||
    item?.medicine_url ||
    "";

  const title =
    safeText(
      item?.title
    ) ||
    safeText(
      item?.id
    ) ||
    "Untitled";

  return (
    <article
      className={
        `result-card ${
          selected
            ? "selected"
            : ""
        }`
      }
    >
      <div
        className="result-top"
      >
        <div
          className="result-meta"
        >
          <SourceBadge
            source={
              item?.source
            }
          />

          {item?.date && (
            <span>
              {safeText(
                item.date
              )}
            </span>
          )}
        </div>

        <button
          type="button"
          className={
            `select-button ${
              selected
                ? "selected"
                : ""
            }`
          }
          onClick={() =>
            onToggle(
              item,
              index
            )
          }
        >
          {selected
            ? "✓ SELECTED"
            : "+ SELECT"}
        </button>
      </div>

      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="result-title"
        >
          {title} ↗
        </a>
      ) : (
        <div
          className="result-title"
        >
          {title}
        </div>
      )}

      <div
        className="result-detail"
      >
        {item?.journal && (
          <span>
            {safeText(
              item.journal
            )}
          </span>
        )}

        {item?.id && (
          <span>
            {safeText(
              item.id
            )}
          </span>
        )}

        {item?.status && (
          <span>
            {safeText(
              item.status
            )}
          </span>
        )}
      </div>

      {(item?.abstract ||
        item?.summary) && (
        <p
          className="abstract"
        >
          {safeText(
            item.abstract ||
            item.summary
          )}
        </p>
      )}
    </article>
  );
}


function SearchPage({
  query,
  setQuery,
  searchLoading,
  searchData,
  runSearch,
  selectedEvidence,
  selectedItems,
  toggleEvidence,
  removeEvidence,
  setPage,
}) {
  const [
    filter,
    setFilter,
  ] = useState("all");

  const results =
    searchData?.results ||
    [];

  const counts =
    searchData?.counts ||
    {};

  const pagination =
    searchData?.pagination ||
    {};

  const currentPage =
    pagination.page ||
    1;

  const filteredItems =
    useMemo(
      () => {
        if (
          filter === "all"
        ) {
          return results;
        }

        return results.filter(
          (item) =>
            normalizeSource(
              item.source
            ) === filter
        );
      },
      [
        results,
        filter,
      ]
    );

  const pubmedCount =
    counts.peer_reviewed ??
    counts.pubmed ??
    results.filter(
      (item) =>
        normalizeSource(
          item.source
        ) === "pubmed"
    ).length;

  const trialCount =
    counts.clinical_trials ??
    counts.trials ??
    results.filter(
      (item) =>
        normalizeSource(
          item.source
        ) === "trials"
    ).length;

  const regulatoryCount =
    counts.regulatory ??
    (
      results.filter(
        (item) =>
          normalizeSource(
            item.source
          ) ===
          "regulatory"
      ).length
    );

  const totalCount =
    counts.total ??
    (
      Number(pubmedCount) +
      Number(trialCount) +
      Number(regulatoryCount)
    );

  const pubmedPages =
    pagination.pubmed_total_pages ||
    0;

  const trialPages =
    pagination.clinical_trials_total_pages ||
    0;

  const maxPages =
    Math.max(
      pubmedPages,
      trialPages,
      pagination.total_pages ||
        0,
      1
    );

  return (
    <>
      <header
        className="page-header"
      >
        <span
          className="eyebrow"
        >
          SEARCH → UNDERSTAND
        </span>

        <h1>
          Smart Search
        </h1>

        <p>
          PubMed, ClinicalTrials.gov,
          FDA and EMA scientific sources.
        </p>
      </header>

      <section
        className="search-box"
      >
        <div
          className="search-row"
        >
          <div
            className="search-field"
          >
            <span>
              ⌕
            </span>

            <input
              value={query}
              placeholder="Search disease, biomarker, treatment, asset or scientific question"
              onChange={(event) =>
                setQuery(
                  event.target.value
                )
              }
              onKeyDown={(event) => {
                if (
                  event.key ===
                  "Enter"
                ) {
                  runSearch(1);
                }
              }}
            />
          </div>

          <button
            type="button"
            className="primary-button search-main-button"
            disabled={
              searchLoading ||
              !query.trim()
            }
            onClick={() =>
              runSearch(1)
            }
          >
            {searchLoading
              ? "Searching..."
              : "Search"}
          </button>
        </div>

        {searchData && (
          <div
            className="count-row"
          >
            <button
              type="button"
              className={
                `count ${
                  filter === "pubmed"
                    ? "active"
                    : ""
                }`
              }
              onClick={() =>
                setFilter(
                  "pubmed"
                )
              }
            >
              <strong>
                {pubmedCount}
              </strong>

              <span>
                PubMed
              </span>
            </button>

            <button
              type="button"
              className={
                `count ${
                  filter === "trials"
                    ? "active"
                    : ""
                }`
              }
              onClick={() =>
                setFilter(
                  "trials"
                )
              }
            >
              <strong>
                {trialCount}
              </strong>

              <span>
                Trials
              </span>
            </button>

            <button
              type="button"
              className={
                `count ${
                  filter ===
                  "regulatory"
                    ? "active"
                    : ""
                }`
              }
              onClick={() =>
                setFilter(
                  "regulatory"
                )
              }
            >
              <strong>
                {regulatoryCount}
              </strong>

              <span>
                Regulatory
              </span>
            </button>

            <button
              type="button"
              className={
                `count ${
                  filter === "all"
                    ? "active"
                    : ""
                }`
              }
              onClick={() =>
                setFilter("all")
              }
            >
              <strong>
                {totalCount}
              </strong>

              <span>
                All
              </span>
            </button>
          </div>
        )}
      </section>

      {!searchData ? (
        <div
          className="empty"
        >
          Search scientific evidence.
        </div>
      ) : (
        <div
          className="results-layout"
        >
          <div>
            <div
              className="results-toolbar"
            >
              <div>
                <span
                  className="tiny-label"
                >
                  SEARCH RESULTS
                </span>

                <strong>
                  {filteredItems.length}
                  {" "}
                  records shown
                </strong>
              </div>

              <span
                className="muted"
              >
                Click SELECT to add evidence
              </span>
            </div>

            <div
              className="results"
            >
              {filteredItems.length ===
              0 ? (
                <div
                  className="mini-empty"
                >
                  No records in this source
                  category on the current page.
                </div>
              ) : (
                filteredItems.map(
                  (
                    item,
                    index
                  ) => {
                    const key =
                      itemKey(
                        item,
                        index
                      );

                    return (
                      <ResultCard
                        key={key}
                        item={item}
                        index={index}
                        selected={
                          Boolean(
                            selectedEvidence[
                              key
                            ]
                          )
                        }
                        onToggle={
                          toggleEvidence
                        }
                      />
                    );
                  }
                )
              )}
            </div>

            <div
              className="pagination"
            >
              <button
                type="button"
                disabled={
                  searchLoading ||
                  currentPage <= 1
                }
                onClick={() =>
                  runSearch(
                    currentPage -
                      1
                  )
                }
              >
                ← Previous
              </button>

              <span>
                Page {currentPage}
                {" / "}
                {maxPages}
              </span>

              <button
                type="button"
                disabled={
                  searchLoading ||
                  currentPage >=
                    maxPages
                }
                onClick={() =>
                  runSearch(
                    currentPage +
                      1
                  )
                }
              >
                Next →
              </button>
            </div>
          </div>

          <aside
            className="basket"
          >
            <div
              className="basket-header"
            >
              <div>
                <span
                  className="tiny-label"
                >
                  EVIDENCE BASKET
                </span>

                <h3>
                  {selectedItems.length}
                  {" "}
                  selected
                </h3>
              </div>
            </div>

            {selectedItems.length ===
            0 ? (
              <div
                className="basket-empty"
              >
                Select evidence from the
                search results.
              </div>
            ) : (
              <>
                <div
                  className="basket-items"
                >
                  {selectedItems.map(
                    (
                      item,
                      index
                    ) => (
                      <div
                        className="basket-item"
                        key={
                          item._selectionKey ||
                          index
                        }
                      >
                        <SourceBadge
                          source={
                            item.source
                          }
                        />

                        {item.url ? (
                          <a
                            href={
                              item.url
                            }
                            target="_blank"
                            rel="noreferrer"
                          >
                            {item.title ||
                              item.id}
                          </a>
                        ) : (
                          <p>
                            {item.title ||
                              item.id}
                          </p>
                        )}

                        <button
                          type="button"
                          aria-label="Remove"
                          onClick={() =>
                            removeEvidence(
                              item._selectionKey
                            )
                          }
                        >
                          ×
                        </button>
                      </div>
                    )
                  )}
                </div>

                <button
                  type="button"
                  className="primary-button full"
                  onClick={() =>
                    setPage(
                      "evidence-analysis"
                    )
                  }
                >
                  Analyze selected →
                </button>
              </>
            )}
          </aside>
        </div>
      )}
    </>
  );
}


/* =========================================================
   LANDSCAPE
   ========================================================= */

function LandscapeTable({
  title,
  items,
}) {
  return (
    <section
      className="panel"
    >
      <span
        className="tiny-label"
      >
        {title}
      </span>

      {items.length === 0 ? (
        <div
          className="mini-empty"
        >
          No records returned.
        </div>
      ) : (
        <div
          className="table-wrap"
        >
          <table>
            <thead>
              <tr>
                <th>Therapy / Asset</th>
                <th>Status</th>
                <th>Phase</th>
                <th>Source</th>
              </tr>
            </thead>

            <tbody>
              {items.map(
                (
                  item,
                  index
                ) => (
                  <tr
                    key={
                      item.id ||
                      item.url ||
                      index
                    }
                  >
                    <td>
                      {item.url ? (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {item.name ||
                            item.title ||
                            item.asset ||
                            item.brand ||
                            item.generic ||
                            "Record"}
                        </a>
                      ) : (
                        item.name ||
                        item.title ||
                        item.asset ||
                        item.brand ||
                        item.generic ||
                        "Record"
                      )}
                    </td>

                    <td>
                      {item.status ||
                        item.approval_status ||
                        "—"}
                    </td>

                    <td>
                      {item.phase ||
                        "—"}
                    </td>

                    <td>
                      {item.source ||
                        "—"}
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}


function LandscapePage({
  disease,
  setDisease,
  asset,
  setAsset,
  biomarker,
  setBiomarker,
  setting,
  setSetting,
  loading,
  data,
  buildLandscape,
}) {
  const approved =
    data?.approved ||
    data?.current ||
    data?.approved_current ||
    [];

  const emerging =
    data?.emerging ||
    data?.investigational ||
    [];

  return (
    <>
      <header
        className="page-header"
      >
        <span
          className="eyebrow"
        >
          UNDERSTAND
        </span>

        <h1>
          Treatment Landscape
        </h1>

        <p>
          Approved/current and emerging
          investigational therapies remain
          separated.
        </p>
      </header>

      <section
        className="landscape-form"
      >
        <label>
          <span>Disease</span>

          <input
            value={disease}
            placeholder="NSCLC"
            onChange={(event) =>
              setDisease(
                event.target.value
              )
            }
          />
        </label>

        <label>
          <span>Biomarker</span>

          <input
            value={biomarker}
            placeholder="ROS1"
            onChange={(event) =>
              setBiomarker(
                event.target.value
              )
            }
          />
        </label>

        <label>
          <span>Setting</span>

          <input
            value={setting}
            placeholder="1L"
            onChange={(event) =>
              setSetting(
                event.target.value
              )
            }
          />
        </label>

        <label>
          <span>My Asset</span>

          <input
            value={asset}
            placeholder="Optional"
            onChange={(event) =>
              setAsset(
                event.target.value
              )
            }
          />
        </label>

        <button
          type="button"
          className="primary-button"
          disabled={
            loading ||
            !disease.trim()
          }
          onClick={
            buildLandscape
          }
        >
          {loading
            ? "Building..."
            : "Build Landscape"}
        </button>
      </section>

      {!data ? (
        <div
          className="empty"
        >
          Enter a disease to build the
          treatment landscape.
        </div>
      ) : (
        <>
          <LandscapeTable
            title="CURRENT / APPROVED"
            items={
              Array.isArray(
                approved
              )
                ? approved
                : []
            }
          />

          <LandscapeTable
            title="EMERGING / INVESTIGATIONAL"
            items={
              Array.isArray(
                emerging
              )
                ? emerging
                : []
            }
          />
        </>
      )}
    </>
  );
}


/* =========================================================
   PATIENT VOICE / HCP INSIGHTS
   ========================================================= */

function PatientSignalCard({
  item,
  index,
}) {
  const url =
    item?.url ||
    item?.permalink ||
    item?.link ||
    "";

  const title =
    item?.title ||
    item?.text ||
    item?.body ||
    item?.content ||
    `Patient Voice signal ${index + 1}`;

  const body =
    item?.body ||
    item?.text ||
    item?.content ||
    item?.summary ||
    "";

  const source =
    item?.subreddit
      ? `r/${item.subreddit}`
      : (
          item?.source ||
          "Reddit"
        );

  return (
    <article
      className="signal-card"
    >
      <div>
        <div
          className="signal-card-tags"
        >
          <span
            className="signal-tag"
          >
            PATIENT VOICE
          </span>

          <span
            className="representative-tag"
          >
            {source}
          </span>
        </div>

        <small>
          {item?.date ||
            item?.created_at ||
            ""}
        </small>
      </div>

      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="signal-title"
        >
          {safeText(title)} ↗
        </a>
      ) : (
        <div
          className="signal-title"
        >
          {safeText(title)}
        </div>
      )}

      {body &&
        body !== title && (
        <p>
          {safeText(body)}
        </p>
      )}

      {url && (
        <a
          className="signal-source-link"
          href={url}
          target="_blank"
          rel="noreferrer"
        >
          Open original Reddit discussion ↗
        </a>
      )}
    </article>
  );
}


function ThemeChip({
  theme,
}) {
  if (
    typeof theme ===
    "string"
  ) {
    return (
      <span
        className="theme-chip"
      >
        {theme}
      </span>
    );
  }

  const name =
    theme?.theme ||
    theme?.name ||
    theme?.label ||
    "Theme";

  const count =
    theme?.count;

  const share =
    theme?.share_pct;

  return (
    <span
      className="theme-chip"
    >
      <strong>
        {name}
      </strong>

      {count !==
        undefined && (
        <small>
          {count}
          {share !== undefined
            ? ` · ${share}%`
            : ""}
        </small>
      )}
    </span>
  );
}


function ListenPage({
  listenQuery,
  setListenQuery,
  listenLoading,
  listenData,
  collectPatientVoice,
  hcpItems,
  hcpTopic,
  setHcpTopic,
  hcpObservation,
  setHcpObservation,
  hcpType,
  setHcpType,
  hcpDate,
  setHcpDate,
  hcpNotes,
  setHcpNotes,
  hcpSaving,
  saveHcpInsight,
  deleteHcpInsight,
  setPage,
}) {
  const patientItems =
    listenData?.items ||
    listenData?.signals ||
    [];

  const analysis =
    listenData?.analysis ||
    {};

  const representativeCount =
    analysis.representative_count ||
    analysis.representative_items
      ?.length ||
    0;

  const topThemes =
    analysis.top_themes ||
    [];

  return (
    <>
      <header
        className="page-header"
      >
        <span
          className="eyebrow"
        >
          LISTEN
        </span>

        <h1>
          Field Intelligence
        </h1>

        <p>
          Patient Voice and HCP field
          signals remain separate from
          scientific evidence.
        </p>
      </header>

      <section
        className="listen-search"
      >
        <div
          className="listen-search-field"
        >
          <span>
            ⌕
          </span>

          <input
            value={listenQuery}
            placeholder="Search disease, treatment, symptom, side effect, unmet need or patient concern"
            onChange={(event) =>
              setListenQuery(
                event.target.value
              )
            }
            onKeyDown={(event) => {
              if (
                event.key ===
                "Enter"
              ) {
                collectPatientVoice();
              }
            }}
          />
        </div>

        <button
          type="button"
          className="primary-button listen-search-button"
          disabled={
            listenLoading ||
            !listenQuery.trim()
          }
          onClick={
            collectPatientVoice
          }
        >
          {listenLoading
            ? "Collecting..."
            : "Collect Patient Voice"}
        </button>
      </section>

      {listenData && (
        <section
          className="patient-voice-panel"
        >
          <div
            className="patient-voice-header"
          >
            <div>
              <span
                className="tiny-label"
              >
                PATIENT VOICE
              </span>

              <h2>
                {listenData.count ||
                  patientItems.length}
                {" "}
                signals aggregated
                {representativeCount >
                  0
                  ? (
                      ` · ${representativeCount}` +
                      " representative signals"
                    )
                  : ""}
              </h2>
            </div>
          </div>

          <div
            className="disclaimer field"
          >
            <strong>
              FIELD SIGNAL
            </strong>

            <p>
              {listenData.disclaimer ||
                "Patient Voice signals are derived from self-selected public online discussions and should not be interpreted as representative patient evidence or validated RWE. Signals are intended for hypothesis generation and Medical Affairs exploration only."}
            </p>
          </div>

          {topThemes.length >
            0 && (
            <div
              className="theme-list"
            >
              {topThemes
                .slice(0, 10)
                .map(
                  (
                    theme,
                    index
                  ) => (
                    <ThemeChip
                      key={index}
                      theme={theme}
                    />
                  )
                )}
            </div>
          )}

          <div
            className="patient-results-head"
          >
            <div>
              <span
                className="tiny-label"
              >
                PUBLIC DISCUSSIONS
              </span>

              <strong>
                {patientItems.length}
                {" "}
                Reddit signals
              </strong>
            </div>

            <small>
              Click title or link to open
              original discussion
            </small>
          </div>

          <div
            className="patient-signal-list"
          >
            {patientItems.length ===
            0 ? (
              <div
                className="mini-empty"
              >
                No public discussions
                returned.
              </div>
            ) : (
              patientItems.map(
                (
                  item,
                  index
                ) => (
                  <PatientSignalCard
                    item={item}
                    index={index}
                    key={
                      item.id ||
                      item.url ||
                      index
                    }
                  />
                )
              )
            )}
          </div>
        </section>
      )}

      <section
        className="hcp-section"
      >
        <div
          className="section-heading-row"
        >
          <div>
            <span
              className="tiny-label"
            >
              FIELD CAPTURE
            </span>

            <h2>
              HCP Insight
            </h2>

            <p>
              Capture observations from
              scientific field interactions.
            </p>
          </div>
        </div>

        <div
          className="hcp-form"
        >
          <label>
            <span>Topic</span>

            <input
              value={hcpTopic}
              placeholder="Scientific topic or question"
              onChange={(event) =>
                setHcpTopic(
                  event.target.value
                )
              }
            />
          </label>

          <label>
            <span>
              Insight type
            </span>

            <select
              value={hcpType}
              onChange={(event) =>
                setHcpType(
                  event.target.value
                )
              }
            >
              <option>
                Unmet need
              </option>

              <option>
                Evidence gap
              </option>

              <option>
                Treatment pattern
              </option>

              <option>
                Competitor
              </option>

              <option>
                Safety
              </option>

              <option>
                Patient journey
              </option>

              <option>
                Scientific question
              </option>
            </select>
          </label>

          <label
            className="full-span"
          >
            <span>
              Observation / Insight
            </span>

            <textarea
              value={hcpObservation}
              placeholder="Capture the scientific observation or unmet need..."
              onChange={(event) =>
                setHcpObservation(
                  event.target.value
                )
              }
            />
          </label>

          <label>
            <span>
              Meeting date
            </span>

            <input
              type="date"
              value={hcpDate}
              onChange={(event) =>
                setHcpDate(
                  event.target.value
                )
              }
            />
          </label>

          <label>
            <span>
              Notes
            </span>

            <input
              value={hcpNotes}
              placeholder="Optional notes"
              onChange={(event) =>
                setHcpNotes(
                  event.target.value
                )
              }
            />
          </label>

          <div
            className="form-actions full-span"
          >
            <button
              type="button"
              className="primary-button"
              disabled={
                hcpSaving ||
                !hcpTopic.trim() ||
                !hcpObservation.trim()
              }
              onClick={
                saveHcpInsight
              }
            >
              {hcpSaving
                ? "Saving..."
                : "Save HCP Insight"}
            </button>
          </div>
        </div>
      </section>

      {hcpItems.length > 0 && (
        <section
          className="hcp-list"
        >
          <div
            className="patient-results-head"
          >
            <div>
              <span
                className="tiny-label"
              >
                SAVED HCP INSIGHTS
              </span>

              <strong>
                {hcpItems.length}
                {" "}
                field signals
              </strong>
            </div>
          </div>

          {hcpItems.map(
            (item) => (
              <article
                className="hcp-card"
                key={item.id}
              >
                <div
                  className="hcp-card-top"
                >
                  <div>
                    <span
                      className="field-tag"
                    >
                      FIELD SIGNAL
                    </span>

                    <span
                      className="type-tag"
                    >
                      {item.insight_type}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() =>
                      deleteHcpInsight(
                        item.id
                      )
                    }
                  >
                    Delete
                  </button>
                </div>

                <h3>
                  {item.topic}
                </h3>

                <p>
                  {item.observation}
                </p>

                {item.notes && (
                  <small>
                    {item.notes}
                  </small>
                )}
              </article>
            )
          )}
        </section>
      )}

      <div
        className="listen-analysis-action"
      >
        <button
          type="button"
          className="primary-button"
          disabled={
            !listenData &&
            hcpItems.length === 0
          }
          onClick={() =>
            setPage(
              "listen-analysis"
            )
          }
        >
          Analyze Insights →
        </button>
      </div>
    </>
  );
}


/* =========================================================
   ANALYSIS
   ========================================================= */

function SelectedEvidencePanel({
  items,
}) {
  return (
    <section
      className="selected-source-panel"
    >
      <div
        className="selected-source-header"
      >
        <div>
          <span
            className="tiny-label"
          >
            SELECTED SOURCES
          </span>

          <h2>
            Evidence Basket
          </h2>
        </div>

        <strong
          className="selected-source-count"
        >
          {items.length}
        </strong>
      </div>

      {items.length === 0 ? (
        <div
          className="mini-empty"
        >
          No scientific evidence selected.
        </div>
      ) : (
        <div
          className="selected-source-list"
        >
          {items.map(
            (
              item,
              index
            ) => (
              <article
                key={
                  item._selectionKey ||
                  item.id ||
                  index
                }
              >
                <div>
                  <SourceBadge
                    source={
                      item.source
                    }
                  />

                  <span
                    className="selected-source-number"
                  >
                    SOURCE {index + 1}
                  </span>
                </div>

                {item.url ? (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {item.title ||
                      item.id ||
                      "Scientific source"} ↗
                  </a>
                ) : (
                  <strong>
                    {item.title ||
                      item.id ||
                      "Scientific source"}
                  </strong>
                )}

                <small>
                  {[
                    item.journal,
                    item.date,
                    item.id,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </small>
              </article>
            )
          )}
        </div>
      )}
    </section>
  );
}


function InsightSourcePanel({
  listenData,
  hcpItems,
}) {
  const patientCount =
    listenData?.count ||
    listenData?.items?.length ||
    0;

  const representative =
    listenData?.analysis
      ?.representative_count ||
    listenData?.analysis
      ?.representative_items
      ?.length ||
    0;

  return (
    <section
      className="selected-source-panel"
    >
      <div
        className="selected-source-header"
      >
        <div>
          <span
            className="tiny-label"
          >
            SOURCE MATERIAL
          </span>

          <h2>
            Field Intelligence
          </h2>
        </div>
      </div>

      <div
        className="signal-summary"
      >
        <div>
          <strong>
            {patientCount}
          </strong>

          <span>
            Patient Voice signals
          </span>
        </div>

        <div>
          <strong>
            {representative}
          </strong>

          <span>
            representative signals
          </span>
        </div>

        <div>
          <strong>
            {hcpItems.length}
          </strong>

          <span>
            HCP field insights
          </span>
        </div>
      </div>

      <p
        className="field-analysis-note"
      >
        Patient Voice represents
        hypothesis-generating field signals,
        not representative patient evidence
        or validated RWE.
      </p>
    </section>
  );
}


function AnalysisReport({
  mode,
  analysisReady,
  loadingFormat,
  exportError,
  onExport,
}) {
  const evidenceMode =
    mode === "evidence";

  return (
    <section
      className="report-section"
    >
      <div
        className="report-section-header"
      >
        <div>
          <span
            className="tiny-label"
          >
            ANALYSIS OUTPUT
          </span>

          <h2>
            {evidenceMode
              ? "Internal Medical Intelligence Report"
              : "HCP Discussion Brief"}
          </h2>
        </div>

        <span
          className={
            `report-status ${
              analysisReady
                ? "ready"
                : ""
            }`
          }
        >
          {analysisReady
            ? "READY"
            : "ANALYSIS REQUIRED"}
        </span>
      </div>

      <div
        className="report-card"
      >
        <div
          className="report-copy"
        >
          <span>
            {evidenceMode
              ? "INTERNAL MEDICAL AFFAIRS"
              : "HCP SCIENTIFIC PREPARATION"}
          </span>

          <h3>
            {evidenceMode
              ? "Internal Medical Intelligence Report"
              : "HCP Discussion Brief"}
          </h3>

          <p>
            {evidenceMode
              ? (
                  "Built from the selected Evidence Basket sources and the completed Evidence Analysis. Includes synthesis, key findings, evidence gaps, Medical Affairs questions, source trace and limitations."
                )
              : (
                  "Built from Patient Voice, saved HCP field insights and the completed Insight Analysis. Includes key scientific themes, potential HCP questions, Listen For, evidence gaps, scientific discussion areas and source trace."
                )}
          </p>
        </div>

        <div
          className="report-actions"
        >
          <button
            type="button"
            disabled={
              !analysisReady ||
              Boolean(
                loadingFormat
              )
            }
            onClick={() =>
              onExport("pdf")
            }
          >
            {loadingFormat ===
            "pdf"
              ? "Generating..."
              : "↓ Download PDF"}
          </button>

          <button
            type="button"
            disabled={
              !analysisReady ||
              Boolean(
                loadingFormat
              )
            }
            onClick={() =>
              onExport("pptx")
            }
          >
            {loadingFormat ===
            "pptx"
              ? "Generating..."
              : "↓ Download PPTX"}
          </button>
        </div>
      </div>

      {!analysisReady && (
        <p
          className="report-helper"
        >
          Run the analysis first. PDF and
          PPTX will become available when
          an analysis result exists.
        </p>
      )}

      {exportError && (
        <div
          className="error"
        >
          {exportError}
        </div>
      )}
    </section>
  );
}


function AnalysisPage({
  mode,
  selectedItems,
  listenData,
  hcpItems,
  analysisPrompt,
  setAnalysisPrompt,
  analysisModel,
  setAnalysisModel,
  analysisLanguage,
  setAnalysisLanguage,
  analysisLoading,
  analysisResult,
  analysisError,
  runAnalysis,
  reportLoadingFormat,
  reportExportError,
  exportAnalysisReport,
}) {
  const isEvidence =
    mode === "evidence";

  const canAnalyze =
    isEvidence
      ? selectedItems.length > 0
      : (
          Boolean(listenData) ||
          hcpItems.length > 0
        );

  return (
    <>
      <header
        className="analysis-page-header"
      >
        <div>
          <span
            className="eyebrow"
          >
            {isEvidence
              ? "UNDERSTAND → ANALYZE"
              : "LISTEN → ANALYZE"}
          </span>

          <h1>
            {isEvidence
              ? "Evidence Analysis"
              : "Insight Analysis"}
          </h1>

          <p>
            {isEvidence
              ? (
                  `${selectedItems.length} selected scientific sources`
                )
              : (
                  `${listenData?.count || 0} Patient Voice signals · ${hcpItems.length} HCP field insights`
                )}
          </p>
        </div>

        <div
          className="analysis-selectors"
        >
          <label>
            <span>
              AI MODEL
            </span>

            <select
              value={analysisModel}
              onChange={(event) =>
                setAnalysisModel(
                  event.target.value
                )
              }
            >
              <option value="gemini">
                Gemini
              </option>
            </select>
          </label>

          <label>
            <span>
              ANALYSIS LANGUAGE
            </span>

            <select
              value={analysisLanguage}
              onChange={(event) =>
                setAnalysisLanguage(
                  event.target.value
                )
              }
            >
              <option value="한국어">
                한국어
              </option>

              <option value="English">
                English
              </option>
            </select>
          </label>
        </div>
      </header>

      {isEvidence ? (
        <SelectedEvidencePanel
          items={selectedItems}
        />
      ) : (
        <InsightSourcePanel
          listenData={listenData}
          hcpItems={hcpItems}
        />
      )}

      <section
        className="analysis-box"
      >
        <div
          className="analysis-guide"
        >
          <strong>
            Ask MSL ONE
          </strong>

          <p>
            {isEvidence
              ? "Analyze only the selected scientific sources. Cross-trial comparisons should not be used to claim superiority."
              : "Analyze field signals for hypothesis generation and scientific preparation without treating Patient Voice as validated evidence."}
          </p>
        </div>

        <textarea
          className="prompt"
          value={analysisPrompt}
          placeholder={
            isEvidence
              ? "예: 선택한 근거를 종합하고 evidence gap, 주요 scientific questions와 Medical Affairs implications를 정리해줘."
              : "예: 주요 field themes, evidence gaps, potential HCP questions와 Listen For를 정리해줘."
          }
          onChange={(event) =>
            setAnalysisPrompt(
              event.target.value
            )
          }
        />

        <div
          className="analysis-button-row"
        >
          <button
            type="button"
            className="primary-button"
            disabled={
              analysisLoading ||
              !canAnalyze
            }
            onClick={() =>
              runAnalysis(mode)
            }
          >
            {analysisLoading
              ? "Gemini 분석 중..."
              : "Analyze"}
          </button>
        </div>
      </section>

      {!canAnalyze && (
        <div
          className="empty"
        >
          {isEvidence
            ? "Select scientific evidence in Smart Search first."
            : "Collect Patient Voice or save an HCP insight first."}
        </div>
      )}

      {analysisError && (
        <div
          className="error"
        >
          {analysisError}
        </div>
      )}

      {analysisResult &&
        !analysisLoading && (
        <section
          className="analysis-result"
        >
          <div
            className="analysis-result-head"
          >
            <div>
              <span
                className="tiny-label"
              >
                MSL ONE ANALYSIS
              </span>

              <h2>
                Gemini Analysis Result
              </h2>
            </div>

            <span
              className="analysis-ready-badge"
            >
              COMPLETE
            </span>
          </div>

          <pre
            className="answer"
          >
            {safeText(
              analysisResult.answer ||
              analysisResult
            )}
          </pre>
        </section>
      )}

      <AnalysisReport
        mode={mode}
        analysisReady={
          Boolean(
            analysisResult
          ) &&
          !analysisLoading
        }
        loadingFormat={
          reportLoadingFormat
        }
        exportError={
          reportExportError
        }
        onExport={(format) =>
          exportAnalysisReport(
            mode,
            format
          )
        }
      />
    </>
  );
}


/* =========================================================
   APP
   ========================================================= */

export default function App() {
  const [
    language,
    setLanguage,
  ] = useState("kr");

  const t =
    TEXT[language];

  const [
    page,
    setPage,
  ] = useState("home");


  const [
    company,
    setCompany,
  ] = useState("GSK");

  const [
    dashboardDisease,
    setDashboardDisease,
  ] = useState("NSCLC");

  const [
    dashboardBiomarker,
    setDashboardBiomarker,
  ] = useState("");

  const [
    dashboardSetting,
    setDashboardSetting,
  ] = useState("");

  const [
    dashboardAsset,
    setDashboardAsset,
  ] = useState("");

  const [
    dashboardData,
    setDashboardData,
  ] = useState(null);

  const [
    dashboardLoading,
    setDashboardLoading,
  ] = useState(false);

  const [
    dashboardError,
    setDashboardError,
  ] = useState("");


  const [
    query,
    setQuery,
  ] = useState("");

  const [
    searchLoading,
    setSearchLoading,
  ] = useState(false);

  const [
    searchData,
    setSearchData,
  ] = useState(null);

  const [
    selectedEvidence,
    setSelectedEvidence,
  ] = useState({});


  const [
    landscapeDisease,
    setLandscapeDisease,
  ] = useState("");

  const [
    landscapeAsset,
    setLandscapeAsset,
  ] = useState("");

  const [
    landscapeBiomarker,
    setLandscapeBiomarker,
  ] = useState("");

  const [
    landscapeSetting,
    setLandscapeSetting,
  ] = useState("");

  const [
    landscapeData,
    setLandscapeData,
  ] = useState(null);

  const [
    landscapeLoading,
    setLandscapeLoading,
  ] = useState(false);


  const [
    listenQuery,
    setListenQuery,
  ] = useState("");

  const [
    listenData,
    setListenData,
  ] = useState(null);

  const [
    listenLoading,
    setListenLoading,
  ] = useState(false);


  const [
    hcpItems,
    setHcpItems,
  ] = useState([]);

  const [
    hcpTopic,
    setHcpTopic,
  ] = useState("");

  const [
    hcpObservation,
    setHcpObservation,
  ] = useState("");

  const [
    hcpType,
    setHcpType,
  ] = useState(
    "Unmet need"
  );

  const [
    hcpDate,
    setHcpDate,
  ] = useState("");

  const [
    hcpNotes,
    setHcpNotes,
  ] = useState("");

  const [
    hcpSaving,
    setHcpSaving,
  ] = useState(false);


  const [
    evidenceAnalysisPrompt,
    setEvidenceAnalysisPrompt,
  ] = useState("");

  const [
    evidenceAnalysisLoading,
    setEvidenceAnalysisLoading,
  ] = useState(false);

  const [
    evidenceAnalysisResult,
    setEvidenceAnalysisResult,
  ] = useState(null);

  const [
    evidenceAnalysisError,
    setEvidenceAnalysisError,
  ] = useState("");


  const [
    listenAnalysisPrompt,
    setListenAnalysisPrompt,
  ] = useState("");

  const [
    listenAnalysisLoading,
    setListenAnalysisLoading,
  ] = useState(false);

  const [
    listenAnalysisResult,
    setListenAnalysisResult,
  ] = useState(null);

  const [
    listenAnalysisError,
    setListenAnalysisError,
  ] = useState("");


  const [
    analysisModel,
    setAnalysisModel,
  ] = useState("gemini");

  const [
    analysisLanguage,
    setAnalysisLanguage,
  ] = useState("한국어");


  const [
    evidenceReportLoading,
    setEvidenceReportLoading,
  ] = useState("");

  const [
    listenReportLoading,
    setListenReportLoading,
  ] = useState("");

  const [
    evidenceReportError,
    setEvidenceReportError,
  ] = useState("");

  const [
    listenReportError,
    setListenReportError,
  ] = useState("");


  const selectedItems =
    useMemo(
      () =>
        Object.values(
          selectedEvidence
        ),
      [selectedEvidence]
    );


  useEffect(() => {
    loadHcpInsights();
  }, []);


  async function loadDashboard() {
    if (
      !dashboardDisease.trim()
    ) {
      return;
    }

    setDashboardLoading(true);
    setDashboardError("");

    try {
      const response =
        await fetch(
          `${API_BASE}/dashboard`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                company,

                disease:
                  dashboardDisease
                    .trim(),

                biomarker:
                  dashboardBiomarker
                    .trim(),

                setting:
                  dashboardSetting
                    .trim(),

                asset:
                  dashboardAsset
                    .trim(),
              }),
          }
        );

      if (!response.ok) {
        throw new Error(
          await response.text()
        );
      }

      setDashboardData(
        await response.json()
      );
    } catch (error) {
      setDashboardError(
        error.message ||
        "Dashboard refresh failed."
      );
    } finally {
      setDashboardLoading(false);
    }
  }


  function sendPaperToEvidence(
    paper,
    index
  ) {
    const key =
      itemKey(
        paper,
        index
      );

    setSelectedEvidence(
      (current) => ({
        ...current,

        [key]: {
          ...paper,

          _selectionKey:
            key,
        },
      })
    );
  }


  async function runSearch(
    requestedPage = 1
  ) {
    if (!query.trim()) {
      return;
    }

    setSearchLoading(true);

    try {
      const response =
        await fetch(
          `${API_BASE}/search`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                query:
                  query.trim(),

                sources: [
                  "PubMed",
                  "ClinicalTrials.gov",
                  "FDA",
                  "EMA",
                ],

                page:
                  requestedPage,

                page_size:
                  20,
              }),
          }
        );

      if (!response.ok) {
        throw new Error(
          await response.text()
        );
      }

      setSearchData(
        await response.json()
      );
    } catch (error) {
      window.alert(
        error.message ||
        "Search failed."
      );
    } finally {
      setSearchLoading(false);
    }
  }


  function toggleEvidence(
    item,
    index
  ) {
    const key =
      itemKey(
        item,
        index
      );

    setSelectedEvidence(
      (current) => {
        const next = {
          ...current,
        };

        if (next[key]) {
          delete next[key];
        } else {
          next[key] = {
            ...item,
            _selectionKey:
              key,
          };
        }

        return next;
      }
    );
  }


  function removeEvidence(
    key
  ) {
    setSelectedEvidence(
      (current) => {
        const next = {
          ...current,
        };

        delete next[key];

        return next;
      }
    );
  }


  async function buildLandscape() {
    if (
      !landscapeDisease.trim()
    ) {
      return;
    }

    setLandscapeLoading(true);

    try {
      const response =
        await fetch(
          `${API_BASE}/landscape`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                disease:
                  landscapeDisease
                    .trim(),

                asset:
                  landscapeAsset
                    .trim(),

                setting:
                  landscapeSetting
                    .trim(),

                biomarker:
                  landscapeBiomarker
                    .trim(),
              }),
          }
        );

      if (!response.ok) {
        throw new Error(
          await response.text()
        );
      }

      setLandscapeData(
        await response.json()
      );
    } catch (error) {
      window.alert(
        error.message ||
        "Landscape failed."
      );
    } finally {
      setLandscapeLoading(false);
    }
  }


  async function collectPatientVoice() {
    if (!listenQuery.trim()) {
      return;
    }

    setListenLoading(true);

    try {
      const response =
        await fetch(
          `${API_BASE}/listen`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                query:
                  listenQuery.trim(),

                limit:
                  PATIENT_FETCH_LIMIT,
              }),
          }
        );

      if (!response.ok) {
        throw new Error(
          await response.text()
        );
      }

      setListenData(
        await response.json()
      );
    } catch (error) {
      window.alert(
        error.message ||
        "Patient Voice collection failed."
      );
    } finally {
      setListenLoading(false);
    }
  }


  async function loadHcpInsights() {
    try {
      const response =
        await fetch(
          `${API_BASE}/hcp-insights`
        );

      if (!response.ok) {
        return;
      }

      const data =
        await response.json();

      setHcpItems(
        data.items ||
        []
      );
    } catch {
      // keep UI usable
    }
  }


  async function saveHcpInsight() {
    if (
      !hcpTopic.trim() ||
      !hcpObservation.trim()
    ) {
      return;
    }

    setHcpSaving(true);

    try {
      const response =
        await fetch(
          `${API_BASE}/hcp-insights`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                topic:
                  hcpTopic.trim(),

                observation:
                  hcpObservation
                    .trim(),

                insight_type:
                  hcpType,

                source:
                  "HCP discussion",

                meeting_date:
                  hcpDate,

                notes:
                  hcpNotes.trim(),
              }),
          }
        );

      if (!response.ok) {
        throw new Error(
          await response.text()
        );
      }

      setHcpTopic("");
      setHcpObservation("");
      setHcpNotes("");

      await loadHcpInsights();
    } catch (error) {
      window.alert(
        error.message ||
        "Save failed."
      );
    } finally {
      setHcpSaving(false);
    }
  }


  async function deleteHcpInsight(
    insightId
  ) {
    try {
      const response =
        await fetch(
          `${API_BASE}/hcp-insights/${insightId}`,
          {
            method: "DELETE",
          }
        );

      if (response.ok) {
        await loadHcpInsights();
      }
    } catch {
      // keep current state
    }
  }


  async function runAnalysis(
    mode
  ) {
    const evidenceMode =
      mode === "evidence";

    if (
      evidenceMode &&
      selectedItems.length ===
        0
    ) {
      return;
    }

    if (
      !evidenceMode &&
      !listenData &&
      hcpItems.length === 0
    ) {
      return;
    }

    if (evidenceMode) {
      setEvidenceAnalysisLoading(
        true
      );

      setEvidenceAnalysisError(
        ""
      );

      setEvidenceAnalysisResult(
        null
      );

      setEvidenceReportError(
        ""
      );
    } else {
      setListenAnalysisLoading(
        true
      );

      setListenAnalysisError(
        ""
      );

      setListenAnalysisResult(
        null
      );

      setListenReportError(
        ""
      );
    }

    try {
      const response =
        await fetch(
          `${API_BASE}/analyze`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                mode,

                prompt:
                  evidenceMode
                    ? evidenceAnalysisPrompt
                    : listenAnalysisPrompt,

                provider:
                  analysisModel,

                language:
                  analysisLanguage,

                evidence:
                  evidenceMode
                    ? selectedItems
                    : [],

                listen:
                  evidenceMode
                    ? null
                    : listenData,

                hcp_insights:
                  evidenceMode
                    ? []
                    : hcpItems,
              }),
          }
        );

      if (!response.ok) {
        throw new Error(
          await response.text()
        );
      }

      const result =
        await response.json();

      if (evidenceMode) {
        setEvidenceAnalysisResult(
          result
        );
      } else {
        setListenAnalysisResult(
          result
        );
      }
    } catch (error) {
      if (evidenceMode) {
        setEvidenceAnalysisError(
          error.message ||
          "Analysis failed."
        );
      } else {
        setListenAnalysisError(
          error.message ||
          "Analysis failed."
        );
      }
    } finally {
      if (evidenceMode) {
        setEvidenceAnalysisLoading(
          false
        );
      } else {
        setListenAnalysisLoading(
          false
        );
      }
    }
  }


  async function exportAnalysisReport(
    mode,
    format
  ) {
    const evidenceMode =
      mode === "evidence";

    const result =
      evidenceMode
        ? evidenceAnalysisResult
        : listenAnalysisResult;

    if (!result) {
      return;
    }

    const setLoading =
      evidenceMode
        ? setEvidenceReportLoading
        : setListenReportLoading;

    const setError =
      evidenceMode
        ? setEvidenceReportError
        : setListenReportError;

    setLoading(format);
    setError("");

    try {
      const response =
        await fetch(
          `${API_BASE}/reports/export/${format}`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                report_type:
                  evidenceMode
                    ? "internal"
                    : "hcp",

                language:
                  analysisLanguage,

                prompt:
                  evidenceMode
                    ? evidenceAnalysisPrompt
                    : listenAnalysisPrompt,

                analysis_result:
                  result,

                evidence:
                  evidenceMode
                    ? selectedItems
                    : [],

                listen:
                  evidenceMode
                    ? null
                    : (
                        listenData ||
                        {
                          items: [],
                          analysis: {},
                        }
                      ),

                hcp_insights:
                  evidenceMode
                    ? []
                    : hcpItems,

                metadata: {
                  provider:
                    analysisModel,

                  language:
                    analysisLanguage,

                  mode,

                  generated_at:
                    result?.generated_at ||
                    "",
                },
              }),
          }
        );

      if (!response.ok) {
        let detail =
          await response.text();

        try {
          const parsed =
            JSON.parse(detail);

          detail =
            parsed.detail ||
            detail;
        } catch {
          // keep raw detail
        }

        throw new Error(detail);
      }

      const blob =
        await response.blob();

      const fallback =
        evidenceMode
          ? (
              `Internal_Medical_Intelligence_Report.${format}`
            )
          : (
              `HCP_Discussion_Brief.${format}`
            );

      const filename =
        parseFilename(
          response.headers.get(
            "content-disposition"
          ),
          fallback
        );

      const objectUrl =
        URL.createObjectURL(
          blob
        );

      const anchor =
        document.createElement(
          "a"
        );

      anchor.href =
        objectUrl;

      anchor.download =
        filename;

      document.body.appendChild(
        anchor
      );

      anchor.click();
      anchor.remove();

      URL.revokeObjectURL(
        objectUrl
      );
    } catch (error) {
      setError(
        `Report export failed: ${
          error.message ||
          "Unknown error"
        }`
      );
    } finally {
      setLoading("");
    }
  }


  let pageContent =
    null;

  if (page === "home") {
    pageContent = (
      <HomePage
        language={language}
        company={company}
        setCompany={setCompany}
        disease={
          dashboardDisease
        }
        setDisease={
          setDashboardDisease
        }
        biomarker={
          dashboardBiomarker
        }
        setBiomarker={
          setDashboardBiomarker
        }
        setting={
          dashboardSetting
        }
        setSetting={
          setDashboardSetting
        }
        asset={
          dashboardAsset
        }
        setAsset={
          setDashboardAsset
        }
        dashboardData={
          dashboardData
        }
        dashboardLoading={
          dashboardLoading
        }
        dashboardError={
          dashboardError
        }
        loadDashboard={
          loadDashboard
        }
        sendPaperToEvidence={
          sendPaperToEvidence
        }
        setPage={setPage}
        listenData={
          listenData
        }
        hcpItems={hcpItems}
      />
    );
  }

  if (page === "search") {
    pageContent = (
      <SearchPage
        query={query}
        setQuery={setQuery}
        searchLoading={
          searchLoading
        }
        searchData={
          searchData
        }
        runSearch={
          runSearch
        }
        selectedEvidence={
          selectedEvidence
        }
        selectedItems={
          selectedItems
        }
        toggleEvidence={
          toggleEvidence
        }
        removeEvidence={
          removeEvidence
        }
        setPage={setPage}
      />
    );
  }

  if (
    page === "landscape"
  ) {
    pageContent = (
      <LandscapePage
        disease={
          landscapeDisease
        }
        setDisease={
          setLandscapeDisease
        }
        asset={
          landscapeAsset
        }
        setAsset={
          setLandscapeAsset
        }
        biomarker={
          landscapeBiomarker
        }
        setBiomarker={
          setLandscapeBiomarker
        }
        setting={
          landscapeSetting
        }
        setSetting={
          setLandscapeSetting
        }
        loading={
          landscapeLoading
        }
        data={
          landscapeData
        }
        buildLandscape={
          buildLandscape
        }
      />
    );
  }

  if (page === "listen") {
    pageContent = (
      <ListenPage
        listenQuery={
          listenQuery
        }
        setListenQuery={
          setListenQuery
        }
        listenLoading={
          listenLoading
        }
        listenData={
          listenData
        }
        collectPatientVoice={
          collectPatientVoice
        }
        hcpItems={hcpItems}
        hcpTopic={hcpTopic}
        setHcpTopic={
          setHcpTopic
        }
        hcpObservation={
          hcpObservation
        }
        setHcpObservation={
          setHcpObservation
        }
        hcpType={hcpType}
        setHcpType={
          setHcpType
        }
        hcpDate={hcpDate}
        setHcpDate={
          setHcpDate
        }
        hcpNotes={hcpNotes}
        setHcpNotes={
          setHcpNotes
        }
        hcpSaving={
          hcpSaving
        }
        saveHcpInsight={
          saveHcpInsight
        }
        deleteHcpInsight={
          deleteHcpInsight
        }
        setPage={setPage}
      />
    );
  }

  if (
    page ===
    "evidence-analysis"
  ) {
    pageContent = (
      <AnalysisPage
        mode="evidence"
        selectedItems={
          selectedItems
        }
        listenData={
          listenData
        }
        hcpItems={hcpItems}
        analysisPrompt={
          evidenceAnalysisPrompt
        }
        setAnalysisPrompt={
          setEvidenceAnalysisPrompt
        }
        analysisModel={
          analysisModel
        }
        setAnalysisModel={
          setAnalysisModel
        }
        analysisLanguage={
          analysisLanguage
        }
        setAnalysisLanguage={
          setAnalysisLanguage
        }
        analysisLoading={
          evidenceAnalysisLoading
        }
        analysisResult={
          evidenceAnalysisResult
        }
        analysisError={
          evidenceAnalysisError
        }
        runAnalysis={
          runAnalysis
        }
        reportLoadingFormat={
          evidenceReportLoading
        }
        reportExportError={
          evidenceReportError
        }
        exportAnalysisReport={
          exportAnalysisReport
        }
      />
    );
  }

  if (
    page ===
    "listen-analysis"
  ) {
    pageContent = (
      <AnalysisPage
        mode="listen"
        selectedItems={
          selectedItems
        }
        listenData={
          listenData
        }
        hcpItems={hcpItems}
        analysisPrompt={
          listenAnalysisPrompt
        }
        setAnalysisPrompt={
          setListenAnalysisPrompt
        }
        analysisModel={
          analysisModel
        }
        setAnalysisModel={
          setAnalysisModel
        }
        analysisLanguage={
          analysisLanguage
        }
        setAnalysisLanguage={
          setAnalysisLanguage
        }
        analysisLoading={
          listenAnalysisLoading
        }
        analysisResult={
          listenAnalysisResult
        }
        analysisError={
          listenAnalysisError
        }
        runAnalysis={
          runAnalysis
        }
        reportLoadingFormat={
          listenReportLoading
        }
        reportExportError={
          listenReportError
        }
        exportAnalysisReport={
          exportAnalysisReport
        }
      />
    );
  }


  return (
    <div
      className="app"
    >
      <aside
        className="sidebar"
      >
        <div
          className="brand"
        >
          <div>
            <strong>
              MSL ONE
            </strong>

            <small>
              Evidence · Insights · Engagement
            </small>
          </div>

          <div
            className="language-toggle"
          >
            <button
              type="button"
              className={
                language === "kr"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setLanguage("kr")
              }
            >
              KR
            </button>

            <button
              type="button"
              className={
                language === "en"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setLanguage("en")
              }
            >
              EN
            </button>
          </div>
        </div>

        <nav>
          <SidebarItem
            active={
              page === "home"
            }
            icon="⌂"
            title={t.home}
            subtitle="Medical Intelligence"
            onClick={() =>
              setPage("home")
            }
          />

          <SidebarItem
            active={
              page === "search"
            }
            icon="⌕"
            title={t.search}
            subtitle="Find scientific evidence"
            onClick={() =>
              setPage("search")
            }
          />

          <SidebarItem
            nested
            active={
              page ===
              "evidence-analysis"
            }
            icon="↳"
            title={
              t.evidenceAnalysis
            }
            subtitle="Selected evidence only"
            onClick={() =>
              setPage(
                "evidence-analysis"
              )
            }
          />

          <SidebarItem
            active={
              page === "landscape"
            }
            icon="◫"
            title={t.landscape}
            subtitle="Paradigm & competition"
            onClick={() =>
              setPage("landscape")
            }
          />

          <SidebarItem
            active={
              page === "listen"
            }
            icon="◉"
            title={t.listen}
            subtitle="Patient & HCP signals"
            onClick={() =>
              setPage("listen")
            }
          />

          <SidebarItem
            nested
            active={
              page ===
              "listen-analysis"
            }
            icon="↳"
            title={
              t.insightAnalysis
            }
            subtitle="Analyze field signals"
            onClick={() =>
              setPage(
                "listen-analysis"
              )
            }
          />
        </nav>

        <div
          className="sidebar-footer"
        >
          <strong>
            Search → Understand
          </strong>

          <span>
            Listen → Analyze → Generate
          </span>
        </div>
      </aside>

      <main>
        <div
          className="content"
        >
          {pageContent}
        </div>
      </main>
    </div>
  );
}