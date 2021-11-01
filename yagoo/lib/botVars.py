# Keep constantly used variable data here

def allSubTypes(capitalize: bool = True):
    """
    Returns all subscription types in the form of a list.

    Arguments
    ---
    capitalize: Returns capitalized strings if set to `True`
    """
    if capitalize:
        return ["Livestream", "Milestone", "Premiere", "Twitter"]
    return ["livestream", "milestone", "premiere", "twitter"]
