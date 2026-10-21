/** Draft preview only. Activation and engineering calculations stay server-owned. */
export function metricPreview(record:any,start = '',end = '') {
  const points=record?.values?.samples;
  if (!Array.isArray(points)||points.length===0) return {points:[],error:'No sample series is recorded. A single value does not establish a trend.'};
  if (points.length>300) return {points:[],error:'The preview supports at most 300 recorded samples.'};
  const boundary=(text:string)=>text?Date.parse(text+(/(?:Z|[+-]\d\d:\d\d)$/i.test(text)?'':'Z')):undefined;
  const first=boundary(start),last=boundary(end);
  if (first!==undefined&&!Number.isFinite(first)||last!==undefined&&!Number.isFinite(last)||first!==undefined&&last!==undefined&&first>last)
    return {points:[],error:'Use a valid UTC window with start before end.'};
  let previous=-Infinity;
  const result:{time:number;value:number|null;timestamp:string}[]=[];
  for (const point of points) {
    if (!point||typeof point!=='object'||Array.isArray(point)) return {points:[],error:'Correct invalid sample records before previewing this series.'};
    const time=typeof point.timestamp==='string'&&/(?:Z|[+-]\d\d:\d\d)$/i.test(point.timestamp)?Date.parse(point.timestamp):NaN;
    const value=point.value??null;
    if (!Number.isFinite(time)||time<=previous||value!==null&&(typeof value!=='number'||!Number.isFinite(value)||value<0||record.values.unit==='percent'&&value>100))
      return {points:[],error:'Correct the sample timestamps and finite numeric values before previewing this series.'};
    previous=time;
    if ((first===undefined||time>=first)&&(last===undefined||time<=last)) result.push({time,value,timestamp:point.timestamp});
  }
  return {points:result,error:result.length?'':'No recorded samples fall inside this UTC window.'};
}
