const $=s=>document.querySelector(s);
let data=null;
try{data=JSON.parse(sessionStorage.getItem('lie-lab-result'));}catch{}
if(!data||!['Lie','Truth',null].includes(data.prediction)){
 $('#simple-verdict').textContent='解析結果がありません';$('#simple-description').textContent='動画を撮影または選択して、解析を実行してください。';$('#result-details').hidden=true;$('#save-result').hidden=true;
}else{
 const lie=data.prediction==='Lie', unknown=data.prediction===null;
 document.body.dataset.verdict=unknown?'unknown':lie?'lie':'truth';
 $('#result-symbol').textContent=unknown?'？':lie?'!':'✓';
 $('#simple-verdict').textContent=unknown?'判定できませんでした':lie?'嘘っぽいです！':'真実っぽいです！';
 $('#simple-description').textContent=unknown?(data.reason||'顔が明るく正面に映る動画で、もう一度お試しください。'):lie?'この動画の顔の動きは、学習データの「嘘」側に近い傾向でした。':'この動画の顔の動きは、学習データの「真実」側に近い傾向でした。';
 $('#result-model').textContent={svm:'集計特徴量＋SVM',gru:'GRU',minirocket:'MiniRocket'}[data.model]||data.model||'—';
 const q=data.quality;$('#result-quality').textContent=q?`有効フレーム ${q.valid_frames} / ${q.total_frames}（${(q.valid_ratio*100).toFixed(1)}%）`:'情報なし';
 const decision=data.lie_decision_score, score=decision??data.lie_score;
 $('#result-score').textContent=Number.isFinite(score)?score.toFixed(3):'—';
 $('#score-explanation').textContent=decision!==undefined?'0を境に、マイナスは「真実」側、プラスは「嘘」側への判定です。例えば −1.5 は真実側のスコアです。数値はモデル内部の尺度で、嘘の確率や正解の確かさではありません。モデル間でも直接比較できません。':data.model==='gru'?'GRUの出力は0.5を境に、それ未満は「真実」側、それ以上は「嘘」側です。この数値は未較正なので、実際に嘘をついている確率としては読めません。':'この数値はモデル内部の未較正スコアです。実際に嘘をついている確率としては読めません。';
}
$('#save-result').onclick=()=>{if(!data)return;const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='lie-lab-result.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
