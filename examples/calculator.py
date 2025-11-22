"""
A simple calculator module for demonstration purposes.
"""

class Calculator:
    """Basic calculator with arithmetic operations"""

    def __init__(self):
        self.memory = 0
        self.history = []

    def add(self, a, b):
        result = a + b
        self.history.append(f"add({a}, {b}) = {result}")
        return result

    def subtract(self, a, b):
        result = a - b
        self.history.append(f"subtract({a}, {b}) = {result}")
        return result

    def multiply(self, a, b):
        result = a * b
        self.history.append(f"multiply({a}, {b}) = {result}")
        return result

    def divide(self, a, b):
        # BUG: No check for division by zero!
        result = a / b
        self.history.append(f"divide({a}, {b}) = {result}")
        return result

    def power(self, base, exponent):
        result = base ** exponent
        self.history.append(f"power({base}, {exponent}) = {result}")
        return result

    def store_memory(self, value):
        self.memory = value

    def recall_memory(self):
        return self.memory

    def clear_history(self):
        self.history = []

    def get_history(self):
        return self.history

    # CODE SMELL: This method is too long and does too much
    def calculate_complex_expression(self, expression):
        parts = expression.split()
        if len(parts) != 3:
            raise ValueError("Invalid expression format")

        left = float(parts[0])
        operator = parts[1]
        right = float(parts[2])

        if operator == '+':
            result = left + right
        elif operator == '-':
            result = left - right
        elif operator == '*':
            result = left * right
        elif operator == '/':
            if right == 0:
                raise ValueError("Cannot divide by zero")
            result = left / right
        elif operator == '**':
            result = left ** right
        else:
            raise ValueError(f"Unknown operator: {operator}")

        self.history.append(f"{expression} = {result}")
        return result


def factorial(n):
    # BUG: No validation for negative numbers
    # BUG: No type checking
    # High complexity due to recursion
    if n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)


def fibonacci(n):
    # PERFORMANCE: Inefficient recursive implementation
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


# Missing docstring
def is_prime(num):
    if num < 2:
        return False
    for i in range(2, int(num ** 0.5) + 1):
        if num % i == 0:
            return False
    return True


# God function - does too many things
def process_numbers(numbers, operation, filter_type=None):
    results = []

    if filter_type == 'even':
        numbers = [n for n in numbers if n % 2 == 0]
    elif filter_type == 'odd':
        numbers = [n for n in numbers if n % 2 != 0]
    elif filter_type == 'prime':
        numbers = [n for n in numbers if is_prime(n)]

    if operation == 'sum':
        return sum(numbers)
    elif operation == 'product':
        result = 1
        for n in numbers:
            result *= n
        return result
    elif operation == 'average':
        if len(numbers) == 0:
            return 0
        return sum(numbers) / len(numbers)
    elif operation == 'factorial':
        return [factorial(n) for n in numbers]
    elif operation == 'fibonacci':
        return [fibonacci(n) for n in numbers]
    else:
        raise ValueError(f"Unknown operation: {operation}")
