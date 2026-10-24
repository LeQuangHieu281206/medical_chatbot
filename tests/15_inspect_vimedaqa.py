from datasets import get_dataset_config_names, load_dataset

NAME = "tmnam20/ViMedAQA"

try:
    configs = get_dataset_config_names(NAME)
except Exception as e:
    print("Không lấy được danh sách cấu hình:", type(e).__name__, e)
    configs = []
print("Cấu hình:", configs)

for cfg in (configs or [None]):
    print("\n" + "=" * 70)
    print("Cấu hình:", cfg)
    ds = load_dataset(NAME, cfg) if cfg else load_dataset(NAME)
    print(ds)
    split = list(ds.keys())[0]
    for row in ds[split].select(range(2)):
        print({k: (str(v)[:200] if v is not None else None) for k, v in row.items()})