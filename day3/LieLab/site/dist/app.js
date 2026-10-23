const $=s=>document.querySelector(s);
let file=null, objectURL=null, busy=false, result=null;
const local=['127.0.0.1','localhost'].includes(location.hostname);
function message(text){$('#status').textContent=text;}
function choose(next){if(busy||cameraActive)return;if(!next)return;if(!/\.(mp4|mov|avi|wmv|webm|mkv)$/i.test(next.name)){message('対応する動画形式を選んでください。');return;}if(next.size===0||next.size>100*1024*1024){message('空ではない100MB以下の動画を選んでください。');return;}file=next;if(objectURL)URL.revokeObjectURL(objectURL);objectURL=URL.createObjectURL(file);$('#preview').src=objectURL;$('#preview-wrap').hidden=false;$('#drop').hidden=true;$('#filename').textContent=file.name+' · '+(file.size/1024/1024).toFixed(1)+' MB';$('#analyze').disabled=false;$('#result').hidden=true;$('#preview-note').hidden=true;message('');}
$('#file').addEventListener('change',e=>choose(e.target.files[0]));
$('#preview').addEventListener('error',()=>{$('#preview-note').hidden=false;});
$('#remove').onclick=()=>{if(!busy)$('#file').click();};
for(const event of ['dragenter','dragover'])$('#drop').addEventListener(event,e=>{e.preventDefault();$('#drop').classList.add('drag');});
for(const event of ['dragleave','drop'])$('#drop').addEventListener(event,e=>{e.preventDefault();$('#drop').classList.remove('drag');if(event==='drop')choose(e.dataTransfer.files[0]);});
async function jsonResponse(response){const data=await response.json();if(!response.ok)throw Error(data.message||'接続に失敗しました');return data;}
function display(data, model){result={model, ...data};$('#result').hidden=false;$('#used-model').textContent={svm:'SVM',gru:'GRU',minirocket:'MiniRocket'}[model];$('#verdict').textContent=data.prediction===null?'判定できませんでした':data.prediction==='Lie'?'嘘ラベルに近い傾向':'真実ラベルに近い傾向';$('#result-description').textContent=data.prediction===null?(data.reason||'顔の検出品質が不足しています。'):'学習データの表情パターンとの比較結果です。この動画の発言が嘘かどうかを証明するものではありません。';const score=data.lie_decision_score??data.lie_score;$('#score').textContent=Number.isFinite(score)?score.toFixed(3):'—';const q=data.quality;$('#quality').textContent=q?`顔の有効フレーム ${q.valid_frames} / ${q.total_frames}（${(q.valid_ratio*100).toFixed(1)}%）`+(data.windows?` · ${data.windows}区間`:''):'';}
$('#analyze').onclick=async()=>{if(!file||busy)return;busy=true;$('#camera-open').disabled=true;document.body.classList.add('busy');$('#analyze').disabled=true;$('#file').disabled=true;$('#result').hidden=true;const model=$('input[name=model]:checked').value;const started=Date.now();try{message('動画を読み込んでいます…');const {job}=await jsonResponse(await fetch('/api/analyze/'+model,{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Video-Suffix':'.'+file.name.split('.').pop().toLowerCase()},body:file}));let done=false;while(!done){message(`顔の動きを解析しています… ${Math.floor((Date.now()-started)/1000)}秒経過。動画の長さによって数分かかります。`);await new Promise(r=>setTimeout(r,1500));const state=await jsonResponse(await fetch('/api/jobs/'+job));if(state.status==='error')throw Error(state.message);if(state.status==='done'){done=true;try{sessionStorage.setItem('lie-lab-result',JSON.stringify({model,...state.result}));location.assign('/result.html');}catch{display(state.result,model);message('結果ページを開けませんでした。この画面に結果を表示しています。');}}}}catch(e){message(e.message==='Failed to fetch'?'解析サーバーに接続できません。ローカルサーバーの起動を確認してください。':e.message);}finally{busy=false;$('#camera-open').disabled=false;document.body.classList.remove('busy');$('#analyze').disabled=!file;$('#file').disabled=false;}};
$('#download').onclick=()=>{if(!result)return;const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='lie-lab-result.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
if(!local){$('#hosted').hidden=false;$('#local').hidden=true;$('#connection').textContent='ローカル解析';}else{fetch('/api/health').then(jsonResponse).then(()=>{$('#connection').textContent='● 解析エンジン接続済み';}).catch(()=>{$('#connection').textContent='未接続';message('解析サーバーを起動して開き直してください。');});}

// Camera access starts only after the visitor presses the camera button.
let cameraActive=false, stream=null, recorder=null, chunks=[], recordedFile=null;
let cameraGeneration=0, recordTimer=null, recordingStarted=0, recordedBytes=0;
let countdownTimer=null;
const cameraStatus=text=>{$('#camera-status').textContent=text;};
function lockInput(locked){$('#mode-friend').disabled=busy;$('#mode-quick').disabled=busy;$('#analyze').disabled=locked||!file||busy;$('#file').disabled=locked||busy;$('#camera-open').disabled=busy;}
function releaseCamera(){if(stream){stream.getTracks().forEach(track=>track.stop());stream=null;}$('#camera-live').srcObject=null;clearInterval(recordTimer);recordTimer=null;}
function closeCamera(){cameraGeneration++;clearInterval(countdownTimer);countdownTimer=null;$('#countdown').hidden=true;if(recorder&&recorder.state!=='inactive')recorder.stop();releaseCamera();cameraActive=false;$('#camera-panel').hidden=true;$('#camera-open').hidden=false;$('#record-start').disabled=true;lockInput(false);}
$('#camera-open').onclick=async()=>{
 if(busy||cameraActive)return;
 if(!navigator.mediaDevices?.getUserMedia||typeof MediaRecorder==='undefined'){cameraStatus('このブラウザでは録画できません。Safari・Chromeなどの対応ブラウザで開くか、動画ファイルを選んでください。');return;}
 const generation=++cameraGeneration;cameraActive=true;lockInput(true);$('#camera-open').hidden=true;$('#camera-panel').hidden=false;$('#record-start').disabled=true;$('#record-stop').hidden=true;$('#record-stop').disabled=false;$('#record-start').hidden=false;cameraStatus('カメラの使用を許可してください。');
 try{const acquired=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:1280},height:{ideal:720},frameRate:{ideal:25,max:30}},audio:false});if(generation!==cameraGeneration){acquired.getTracks().forEach(t=>t.stop());return;}stream=acquired;$('#camera-live').srcObject=stream;await $('#camera-live').play();if(generation!==cameraGeneration)return;$('#record-start').disabled=false;$('#record-time').textContent='00:00 / 01:30';refreshMode();stream.getVideoTracks()[0].addEventListener('ended',()=>{if(cameraActive){closeCamera();cameraStatus('カメラの接続が終了しました。');}});
 }catch(error){if(generation!==cameraGeneration)return;closeCamera();cameraStatus(error.name==='NotAllowedError'?'カメラが許可されていません。ブラウザのカメラ設定で許可してから再度お試しください。':error.name==='NotFoundError'?'カメラが見つかりません。接続を確認してください。':'カメラを起動できませんでした。他のアプリで使用中でないか確認してください。');}
};
function beginRecording(){
 if(!stream||!cameraActive)return;
 try{const mime=['video/webm;codecs=vp8','video/webm','video/mp4'].find(type=>MediaRecorder.isTypeSupported(type));recorder=new MediaRecorder(stream,mime?{mimeType:mime}:undefined);chunks=[];recordedBytes=0;recordingStarted=Date.now();$('#record-start').hidden=true;$('#record-stop').hidden=false;$('#record-download').hidden=true;cameraStatus('● 回答を録画中！ 話し終わったら「回答おわり」を押してね。');
 recorder.ondataavailable=event=>{if(event.data.size){chunks.push(event.data);recordedBytes+=event.data.size;if(recordedBytes>90*1024*1024&&recorder.state==='recording')recorder.stop();}};
 recorder.onstop=()=>{const type=recorder.mimeType||chunks[0]?.type||'video/webm';const blob=new Blob(chunks,{type});chunks=[];closeCamera();if(!blob.size){cameraStatus('録画データがありません。もう一度お試しください。');return;}recordedFile=new File([blob],'recording-'+new Date().toISOString().replace(/[:.]/g,'-')+(type.includes('mp4')?'.mp4':'.webm'),{type});$('#record-download').hidden=false;if(local){choose(recordedFile);cameraStatus('録画できました。動画を確認して「いざ、ウソ発見！」を押してください。');}else{cameraStatus('録画できました。動画を保存し、ローカル解析画面で選択してください。');}};
 recorder.onerror=()=>{cameraStatus('録画中にエラーが発生しました。撮り直してください。');closeCamera();};
 recorder.start(1000);recordTimer=setInterval(()=>{const seconds=Math.floor((Date.now()-recordingStarted)/1000);$('#record-time').textContent=String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0')+' / 01:30';if(seconds>=90&&recorder.state==='recording')recorder.stop();},250);
 }catch(error){closeCamera();cameraStatus('録画を開始できませんでした。別のブラウザでお試しください。');}
};
$('#record-start').onclick=()=>{
 if(!stream||!cameraActive||countdownTimer!==null)return;
 $('#mode-friend').disabled=true;$('#mode-quick').disabled=true;
 const generation=cameraGeneration;let remaining=playMode==='quick'?5:3;
 if(playMode==='quick'){const next=(lastQuestion+1+Math.floor(Math.random()*(challenges.length-1)))%challenges.length;lastQuestion=next;$('#record-question').textContent=challenges[next];$('#question-caption').textContent='5秒で答えを決めよう！';}$('#record-start').disabled=true;$('#countdown').hidden=false;$('#countdown').textContent=remaining;cameraStatus('カウントダウン中。この時間は録画されません。');
 countdownTimer=setInterval(()=>{if(generation!==cameraGeneration){clearInterval(countdownTimer);countdownTimer=null;return;}remaining--;if(remaining>0){$('#countdown').textContent=remaining;}else{clearInterval(countdownTimer);countdownTimer=null;$('#countdown').hidden=true;beginRecording();}},1000);
};
$('#record-stop').onclick=()=>{if(recorder?.state==='recording'){recorder.stop();$('#record-stop').disabled=true;}};
$('#camera-close').onclick=()=>{closeCamera();$('#record-stop').disabled=false;cameraStatus('カメラを終了しました。');};
$('#record-download').onclick=()=>{if(!recordedFile)return;const url=URL.createObjectURL(recordedFile);const a=document.createElement('a');a.href=url;a.download=recordedFile.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
window.addEventListener('pagehide',closeCamera);


const challenges=[
'友達に「見たよ！」と言った作品、本当は見ていなかったことある？',
'「今向かってる」と言いながら、まだ家にいたことある？',
'人の話を聞いていないのに、うなずいたことある？',
'「忙しい」と断って、実は家でゴロゴロしていたことある？',
'もらったプレゼントに、ちょっと大げさに喜んだことある？',
'わからない言葉を、知っているふりしたことある？',
'ゲームで負けたとき、操作のせいにしたことある？',
'集合写真で、まず自分の顔から確認する？',
'「あと5分だけ」と言って、30分以上寝たことある？',
'「全然勉強してない」と言って、実は準備していたことある？',
'相手に合わせて「それ好き！」と言ったことある？',
'メッセージに気づいているのに、気づいていないふりしたことある？',
'部屋の片付けで、とりあえず見えない所に押し込むことある？',
'失敗した料理を「こういう味」と言って出したことある？',
'ひと口ちょうだいと言って、大きくひと口もらったことある？',
'鏡の前で、かっこいい表情を練習したことある？'
];
let playMode='friend', lastQuestion=-1;
function modeLocked(){return busy||countdownTimer!==null||recorder?.state==='recording';}
function refreshMode(){
 $('#mode-friend').setAttribute('aria-pressed',String(playMode==='friend'));$('#mode-quick').setAttribute('aria-pressed',String(playMode==='quick'));
 $('#mode-help').textContent=playMode==='quick'?'質問はまだ秘密。「質問に答える」を押すと質問が出て、5秒後に録画スタート！':'相手に質問してもらい、答える準備ができたらスタート。3秒後に録画するよ。';
 $('#question-caption').textContent=playMode==='quick'?'抜き打ち質問 / ボタンを押すまで秘密！':'質問は相手にしてもらおう';
 $('#record-question').textContent=playMode==='quick'?'？？？ どんな質問が来るかな？':'相手の質問を聞いたら、「質問に答える」を押してね。';
 $('#record-start').textContent=playMode==='quick'?'▶ 質問に答える（質問公開＋5秒）':'▶ 質問に答える（3秒後に録画）';
 if(cameraActive&&stream)cameraStatus(playMode==='quick'?'カメラ準備OK！ 質問に答えるボタンで、抜き打ちチャレンジ開始。':'カメラ準備OK！ 相手に質問してもらおう。');
}
$('#mode-friend').onclick=()=>{if(modeLocked())return;playMode='friend';refreshMode();};
$('#mode-quick').onclick=()=>{if(modeLocked())return;playMode='quick';refreshMode();};
refreshMode();
