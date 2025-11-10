"""Test file with intentional bugs to demonstrate analyzer."""


def process_user_data(data):
    """Process user data - has multiple issues."""
    # Issue 1: No validation
    user = data.get("user")

    # Issue 2: Potential None access
    if user.is_active:  # user might be None!
        # Issue 3: Unclosed file
        f = open("log.txt", "a")
        f.write(user.name)

        # Issue 4: Bare except
        try:
            result = complex_operation(user)
        except:  # Catches everything!
            pass

    return user.id


def complex_nested_logic(x, y, z):
    """Overly complex function - high cyclomatic complexity."""
    if x > 0:
        if y > 0:
            if z > 0:
                if x > y:
                    if y > z:
                        if x > z:
                            if x > 100:
                                if y > 50:
                                    if z > 25:
                                        return True
    return False
