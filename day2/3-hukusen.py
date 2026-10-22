import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('./day1/2-2.csv')
df.columns = df.columns.str.strip()

df["Smile Score"] = (df["AU12_r"] > 2).astype(int)
df["AU04"] = (df["AU04_r"] > 1).astype(int)
df["Head movement"] = (df['pose_Rz'].diff() < -0.005).astype(int)
df["Blink"] = (df["AU45_c"] > 0).astype(int)


fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True)

# Smile Scoreのグラフ
axes[0].plot(df['timestamp'], df["Smile Score"], color="tab:blue")
axes[0].set_ylabel("Smile Score")
axes[0].legend(["Smile Score"], loc="upper right")

# AU04のグラフ
axes[1].plot(df['timestamp'], df["AU04"], color="tab:orange")
axes[1].set_ylabel("AU04")
axes[1].legend(["AU04"], loc="upper right")

# Head movementのグラフ
axes[2].plot(df['timestamp'], df["Head movement"], color="tab:green")
axes[2].set_ylabel("Head movement")
axes[2].legend(["Head movement"], loc="upper right")

# Blinkのグラフ
axes[3].plot(df['timestamp'], df["Blink"], color="tab:red")
axes[3].set_ylabel("Blink")
axes[3].set_xlabel("Time[s]")
axes[3].legend(["Blink"], loc="upper right")

plt.tight_layout()
plt.show()