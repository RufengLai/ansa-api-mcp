import ansa
from ansa import base

# File path
ANSA_FILE = r"D:\claude_space\ansa_test\demo\kunlun_40.03.ansa"

# Renumber PID start
PID_START = 100


def main():
    # Step 1: Open the ANSA file
    print("Opening file: {}".format(ANSA_FILE))
    result = base.Open(ANSA_FILE)
    if result != 1:
        print("base.Open failed, trying utils.Merge...")
        from ansa import utils
        result = utils.Merge(filename=ANSA_FILE, model_action="overwrite_model")
        if result != 1:
            print("ERROR: Cannot open file!")
            return
    print("File opened successfully.")

    # Step 2: Get current deck
    deck = base.CurrentDeck()
    print("Current deck: {}".format(deck))

    # Step 3: Collect all properties
    print("Collecting all properties...")
    properties = base.CollectEntities(deck, None, "__PROPERTIES__", True)
    if not properties:
        print("ERROR: No properties found in the model!")
        return
    print("Found {} properties.".format(len(properties)))

    # Step 4: Renumber properties starting from PID_START
    print("Renumbering properties from PID {}...".format(PID_START))
    new_id = PID_START
    success_count = 0
    fail_count = 0

    for prop in properties:
        result = base.SetEntityId(prop, new_id, True, False)
        if result == 1:
            success_count += 1
        else:
            fail_count += 1
            print("  WARNING: Failed to set PID {} on entity {}".format(new_id, prop))
        new_id += 1

    print("\nDone! {} properties renumbered from PID {} to PID {}.".format(
        success_count, PID_START, PID_START + success_count - 1))
    if fail_count > 0:
        print("{} properties failed to renumber.".format(fail_count))


if __name__ == "__main__":
    main()
