import {useEffect, useRef} from 'react';
import {mountDemo} from './demo.mjs';
import css from './cvrm.css?inline';
import compact from './compact.css?inline';

export default function CvrmPage({lang, onLegacy}) {
 const root=useRef(null);
 useEffect(()=>mountDemo(root.current,lang,{onLegacy}),[lang, onLegacy]);
 return <><style id="cvrm-style">{css+'\n'+compact}</style><div ref={root}/></>;
}
