from datasets import load_dataset

DATASETS = ["tarudesu/ViHealthQA", "hungnm/vietnamese-medical-qa"]

for name in DATASETS:
    print("=" * 60)
    print(name)
    ds = load_dataset(name)
    print(ds)  # các split và số dòng

    split = list(ds.keys())[0]
    df = ds[split].to_pandas()
    print("Cột:", list(df.columns))
    print("Số dòng:", len(df))
    print("Số dòng thiếu dữ liệu:\n", df.isna().sum())

    for col in df.columns:
        if df[col].dtype == object:
            print(f"Độ dài trung bình cột '{col}':", int(df[col].astype(str).str.len().mean()))

    print("Mẫu 2 dòng đầu:")
    print(df.head(2).to_dict(orient="records"))