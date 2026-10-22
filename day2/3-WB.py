import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import cv2

# 1. データの読み込み
df = pd.read_csv('./day2/2-2.csv')
df.columns = df.columns.str.strip()
video_path = './day2/2-2.avi' # 同じフォルダにある動画ファイル

# 特徴量計算 (元のコードと同様)
df["AU04"] = (df["AU04_r"] > 1).astype(int)
df["Head movement"] = (df['pose_Rz'].diff() < -0.005).astype(int)

# 2. グラフ領域のレイアウト作成
fig = plt.figure(figsize=(10, 10))
# 上から比率 2 : 1 : 1 で3段に分割
gs = fig.add_gridspec(3, 1, height_ratios=[2, 1, 1])

ax_video = fig.add_subplot(gs[0])
ax_au = fig.add_subplot(gs[1])
ax_head = fig.add_subplot(gs[2], sharex=ax_au)

# --- 中段・下段のグラフ描画 ---
ax_au.plot(df['timestamp'], df["AU04"], color="tab:orange", label="AU04")
ax_au.set_ylabel("AU04")
ax_au.legend(loc="upper right")

ax_head.plot(df['timestamp'], df["Head movement"], color="tab:green", label="Head movement")
ax_head.set_ylabel("Head movement")
ax_head.set_xlabel("Time[s]")
ax_head.legend(loc="upper right")

# 動画の現在時刻に同期して動かす「赤い縦線」
line_au = ax_au.axvline(x=0, color='red', linestyle='--', linewidth=2)
line_head = ax_head.axvline(x=0, color='red', linestyle='--', linewidth=2)

# --- 上段の動画設定 ---
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
if fps == 0: fps = 30 # 安全対策

ret, frame = cap.read()
if ret:
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    im = ax_video.imshow(frame_rgb)
ax_video.axis('off') # 軸を隠す
ax_video.set_title("Video")

# 3. アニメーション更新関数 (コマごとに呼ばれる)
def update(frame_idx):
    # CSVの長さを超えたら終了処理
    if frame_idx >= len(df):
        return im, line_au, line_head

    # 動画から1フレーム読み込み
    ret, frame = cap.read()
    if ret:
        # OpenCVはBGRなのでRGBに変換して表示
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        im.set_data(frame_rgb)
    
    # グラフの縦線を現在のフレームの時刻に移動
    current_time = df['timestamp'].iloc[frame_idx]
    line_au.set_xdata([current_time, current_time])
    line_head.set_xdata([current_time, current_time])

    return im, line_au, line_head

# FuncAnimationでアニメーションを実行
ani = animation.FuncAnimation(
    fig, update, frames=len(df), 
    interval=1000/fps, # FPSに合わせた更新間隔(ミリ秒)
    blit=True
)

plt.tight_layout()
plt.show()

cap.release()
