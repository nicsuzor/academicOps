"""stats.py — compute the median of a small documented list of numbers.

Documented expected behaviour: for DATA = [10, 2, 8, 4, 6], the median (the
middle value once the numbers are sorted: [2, 4, 6, 8, 10]) should be 6.
"""


def median(nums):
    """Return the median of nums."""
    n = len(nums)
    mid = n // 2
    if n % 2 == 0:
        return (nums[mid - 1] + nums[mid]) / 2
    return nums[mid]


if __name__ == "__main__":
    DATA = [10, 2, 8, 4, 6]
    print(f"median of {DATA}: {median(DATA)}")
