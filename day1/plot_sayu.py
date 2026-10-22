import pandas as pd
import matplotlib.pyplot as plt

# CSVファイルの読み込み
df = pd.read_csv('Sayu.csv')

# 列名の不要な空白を削除
df.columns = df.columns.str.strip()

# グラフの作成 (pose_Rx, pose_Ry, pose_Rz をプロット)
plt.figure(figsize=(12, 6))
plt.plot(df['timestamp'], df['pose_Rx'], label='pose_Rx (Pitch)', alpha=0.8)
plt.plot(df['timestamp'], df['pose_Ry'], label='pose_Ry (Yaw)', alpha=0.8)
plt.plot(df['timestamp'], df['pose_Rz'], label='pose_Rz (Roll)', alpha=0.8)

# グラフの装飾
plt.xlabel('Timestamp (seconds)')
plt.ylabel('Angle (radians)')
plt.title('Head Pose from Sayu.csv')
plt.legend()
plt.grid(True)
plt.tight_layout()

# 画像として保存
plt.savefig('Sayu_pose.png')
print("グラフを Sayu_pose.png として保存しました。")
