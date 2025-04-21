import os
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import matplotlib.pyplot as plt

# 設定桌面的資料夾路徑
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
main_folder = os.path.join(desktop_path, "Health_Care_Institutions")
csv_folder = os.path.join(main_folder, "csv")
excel_folder = os.path.join(main_folder, "excel")
visualization_folder = os.path.join(main_folder, "visualizations")
log_folder = os.path.join(main_folder, "log")
os.makedirs(csv_folder, exist_ok=True)
os.makedirs(excel_folder, exist_ok=True)
os.makedirs(visualization_folder, exist_ok=True)
os.makedirs(log_folder, exist_ok=True)

# 產生新的 log 檔案
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_folder, "log_{}.txt".format(current_time))

# 定義日記記錄函數
def log_message(message):
    """將訊息寫入日記檔案並印出"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = "[{}] {}\n".format(timestamp, message)
    print(log_entry.strip())
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(log_entry)

# 設定要處理的 URL 和對應的檔案名稱
hospital_data = [
    {"url": "https://info.nhi.gov.tw/IODE0000/IODE0000S09?id=325", "file_name": "Medical_Centers"},
    {"url": "https://info.nhi.gov.tw/IODE0000/IODE0000S09?id=326", "file_name": "Regional_Hospitals"},
    {"url": "https://info.nhi.gov.tw/IODE0000/IODE0000S09?id=327", "file_name": "District_Hospitals"}
]

# 設定 Chrome 選項
options = webdriver.ChromeOptions()
prefs = {"download.default_directory": csv_folder}  # 設定下載目錄為 csv 資料夾
options.add_experimental_option("prefs", prefs)

# 翻譯分區業務組對應的英文名稱
area_translation = {
    "臺北業務組": "Taipei_Division",
    "北區業務組": "Northern_Division",
    "中區業務組": "Central_Division",
    "南區業務組": "Southern_Division",
    "高屏業務組": "Kaoping_Division",
    "東區業務組": "Eastern_Division"
}

# 初始化 WebDriver
driver = webdriver.Chrome(options=options)

try:
    all_data = []  # 用於彙整所有資料的列表

    for hospital in hospital_data:
        log_message("Processing: {} (URL: {})".format(hospital['file_name'], hospital['url']))

        # 打開目標網址
        driver.get(hospital["url"])

        # 等待按鈕加載並模擬點擊
        wait = WebDriverWait(driver, 10)
        download_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'rId=')]")))
        download_button.click()
        log_message("Download button clicked. Downloading file...")

        # 等待文件下載完成
        time.sleep(5)

        # 找到最新的 CSV 文件
        csv_files = [f for f in os.listdir(csv_folder) if f.endswith(".csv")]
        if not csv_files:
            raise Exception("No CSV file found (URL: {})".format(hospital['url']))

        # 假設最新下載的 CSV 文件是列表中最後修改的文件
        csv_files = sorted(csv_files, key=lambda f: os.path.getmtime(os.path.join(csv_folder, f)), reverse=True)
        csv_file_path = os.path.join(csv_folder, csv_files[0])

        # 為今天的檔案命名
        today_date = datetime.now().strftime("%Y%m%d")
        today_file_path = os.path.join(csv_folder, "{}_{}.csv".format(hospital['file_name'], today_date))
        os.rename(csv_file_path, today_file_path)
        log_message("File renamed to: {}".format(today_file_path))

        # 讀取 CSV 並新增英文欄位
        df_today = pd.read_csv(today_file_path, encoding="utf-8")
        df_today["Division"] = df_today["分區業務組"].map(area_translation)
        df_today["Hospital_Type"] = hospital["file_name"]

        # 檢查昨天的檔案是否存在
        yesterday_date = (datetime.now() - pd.Timedelta(days=1)).strftime("%Y%m%d")
        yesterday_file_path = os.path.join(csv_folder, "{}_{}.csv".format(hospital["file_name"], yesterday_date))

        if os.path.exists(yesterday_file_path):
            # 比對今天和昨天的檔案內容
            df_yesterday = pd.read_csv(yesterday_file_path, encoding="utf-8")

            if df_today.equals(df_yesterday):
                log_message("{} 資料未變更，刪除今天的檔案：{}".format(hospital["file_name"], today_file_path))
                os.remove(today_file_path)  # 如果檔案相同，刪除今天的檔案
                continue
            else:
                log_message("{} 資料已更新，保存今天的檔案".format(hospital["file_name"]))
        else:
            log_message("{} 沒有昨天的檔案，直接保存今天的檔案".format(hospital["file_name"]))

        # 保存轉換為 Excel 的檔案
        excel_file_path = os.path.join(excel_folder, "{}_{}.xlsx".format(hospital["file_name"], today_date))
        df_today.to_excel(excel_file_path, index=False)
        log_message("檔案已轉存為 Excel：{}".format(excel_file_path))

        # 添加到彙整資料列表
        all_data.append(df_today)

    # 彙整資料並繪製圖表
    if all_data:
        combined_data = pd.concat(all_data, ignore_index=True)
        stacked_data = combined_data.groupby(["Division", "Hospital_Type"]).size().unstack(fill_value=0)

        # 確保醫院類型的順序為醫學中心、區域醫院、地區醫院
        column_order = ["Medical_Centers", "Regional_Hospitals", "District_Hospitals"]
        stacked_data = stacked_data[column_order]

        # 排序數據由小到大
        stacked_data["Total"] = stacked_data.sum(axis=1)
        stacked_data = stacked_data.sort_values("Total")

        # 繪製堆疊直條圖
        stacked_data.drop(columns=["Total"]).plot(
            kind="bar",
            stacked=True,
            figsize=(12, 7),
            color=["skyblue", "lightgreen", "salmon"],
            edgecolor="black"
        )
        plt.title("Distribution of Hospitals by Division and Type", fontsize=16)
        plt.xlabel("Division", fontsize=14)
        plt.ylabel("Number of Institutions", fontsize=14)
        plt.xticks(rotation=45, fontsize=12)
        plt.legend(title="Hospital Type", fontsize=12, title_fontsize=14)
        plt.tight_layout()

        chart_path = os.path.join(visualization_folder, "Hospital_Distribution_Stacked_{}.png".format(today_date))
        plt.savefig(chart_path, dpi=300)
        log_message("Stacked bar chart saved to: {}".format(chart_path))
        plt.show()

        # 繪製單獨表格
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.axis("tight")
        ax.axis("off")
        stacked_data["Total"] = stacked_data.sum(axis=1)  # 確保表格中包含 Total 欄位
        table = plt.table(
            cellText=stacked_data.values,
            rowLabels=stacked_data.index,
            colLabels=stacked_data.columns,
            cellLoc="center",
            loc="center",
            bbox=[0, 0, 1, 1]
        )

        table_path = os.path.join(visualization_folder, "Hospital_Distribution_Table_{}.png".format(today_date))
        plt.savefig(table_path, dpi=300, bbox_inches="tight")
        log_message("Table saved to: {}".format(table_path))
        plt.show()

        # 繪製圓餅圖
        pie_data = stacked_data.drop(columns=["Total"]).sum()
        pie_data = pie_data[column_order]  # 確保圓餅圖的順序一致
        plt.figure(figsize=(8, 8))
        plt.pie(
            pie_data,
            labels=pie_data.index,
            autopct="%1.1f%%",
            startangle=90,
            colors=["skyblue", "lightgreen", "salmon"]
        )
        plt.title("Proportion of Hospital Types", fontsize=16)
        pie_path = os.path.join(visualization_folder, "Hospital_Distribution_Pie_{}.png".format(today_date))
        plt.savefig(pie_path, dpi=300)
        log_message("Pie chart saved to: {}".format(pie_path))
        plt.show()

except Exception as e:
    log_message("Error occurred: {}".format(e))

finally:
    driver.quit()
    log_message("Process completed.")
