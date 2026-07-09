"""metrics.py — small statistics helpers used by pipeline.py."""


def mean(nums):
    """Return the arithmetic mean of nums."""
    return sum(nums) / len(nums)


def median(nums):
    """Return the median of nums."""
    n = len(nums)
    mid = n // 2
    if n % 2 == 0:
        return (nums[mid - 1] + nums[mid]) / 2
    return nums[mid]
