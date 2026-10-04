import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

class PredictiveAnalysis:
    def __init__(self, csv_path="data/user_activity.csv"):
        self.df = pd.read_csv(csv_path)

        self.df["date"] = pd.to_datetime(self.df["date"])
        self.df = self.df.groupby("date")["count"].sum().reset_index()

    def predict_next_trend(self):
        """
        Use Linear Regression to predict next day's trend (total count).
        """
        self.df["day_num"] = np.arange(len(self.df))

        X = self.df[["day_num"]]
        y = self.df["count"]
        model = LinearRegression()
        model.fit(X, y)

        next_day = np.array([[self.df["day_num"].max() + 1]])
        prediction = model.predict(next_day)[0]
        return prediction

    def plot_trend(self, save_path="static/trend_plot.png"):
        """
        Optional: save plot for admin dashboard
        """
        plt.figure(figsize=(6, 4))
        plt.plot(self.df["date"], self.df["count"], marker='o', label="Actual")
        plt.title("User Activity Trend")
        plt.xlabel("Date")
        plt.ylabel("Activity Count")
        plt.legend()
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
