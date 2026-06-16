from src.statistics import calculate_overall_statistics, calculate_error_by_ticker


overall_stats = calculate_overall_statistics()
ticker_stats = calculate_error_by_ticker()

print("Overall Accuracy Statistics")
print("---------------------------")
print("Total Matches:", overall_stats["total_matches"])
print("Valid Matches:", overall_stats["valid_matches"])
print("Invalid Matches:", overall_stats["invalid_matches"])
print("Average Absolute Error %:", overall_stats["average_absolute_error"])
print("Median Absolute Error %:", overall_stats["median_absolute_error"])
print("Min Absolute Error %:", overall_stats["min_absolute_error"])
print("Max Absolute Error %:", overall_stats["max_absolute_error"])
print("Standard Deviation Error %:", overall_stats["standard_deviation_error"])

print()
print("Error by Ticker")
print("---------------")
print(ticker_stats)