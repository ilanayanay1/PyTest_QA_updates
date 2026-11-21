import sys
from pathlib import Path

# setting sys.path to run from examples/ directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.testing.test_framework import AmmeterTestFramework


def plot_ammeter_comparison(reports: dict, output_path: Path) -> None:
    #create ammeters graff by matplotlib
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is not installed; skipping chart generation.")
        return

    ammeters = list(reports.keys())
    means = [reports[k]["statistics"].get("mean") or 0.0 for k in ammeters]
    std_devs = [reports[k]["statistics"].get("std_dev") or 0.0 for k in ammeters]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

    # avarage
    ax1.bar(ammeters, means, yerr=std_devs, capsize=6)
    ax1.set_title("Mean Current by Ammeter Type")
    ax1.set_ylabel("Current (A)")
    ax1.grid(axis="y", linestyle="--", alpha=0.5)

    #samples for each ammeter
    for name in ammeters:
        samples = reports[name].get("samples", [])
        if samples:
            ax2.plot(range(1, len(samples) + 1), samples, marker="o", label=name)
    ax2.set_title("Samples Over Test Run")
    ax2.set_xlabel("Sample #")
    ax2.set_ylabel("Current (A)")
    ax2.legend()
    ax2.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Comparison chart saved to: {output_path}")


def main() -> None:
    framework = AmmeterTestFramework(config_path=str(PROJECT_ROOT / "config" / "config.yaml"))
    ammeter_types = ["greenlee", "entes", "circutor"]
    reports = {}

    for ammeter in ammeter_types:
        print(f"Running test for: {ammeter}")
        report = framework.run_test(ammeter)
        reports[ammeter] = report
        stats = report["statistics"]
        print(
            f"  -> status={report['status']}, "
            f"mean={stats.get('mean')}, median={stats.get('median')}, "
            f"std_dev={stats.get('std_dev')}, min={stats.get('min')}, max={stats.get('max')}"
        )

    # comparing result according to test id
    test_ids = [reports[a]["test_id"] for a in ammeter_types]
    comparison = framework.compare_results(test_ids)
    print("\nComparison summary:", comparison)

    # create comparation graff
    chart_file = PROJECT_ROOT / "results" / "ammeters_comparison.png"
    plot_ammeter_comparison(reports, chart_file)


if __name__ == "__main__":
    main()