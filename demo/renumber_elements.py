import ansa
from ansa import base
from ansa import utils

# File path
ANSA_FILE = r"D:\claude_space\ansa_test\demo\kunlun_40.03.ansa"

# Renumber range
RENUMBER_FROM = 1000
RENUMBER_TO = 60000000


def main():
    # Step 1: Open the ANSA file
    print("Opening file: {}".format(ANSA_FILE))
    result = base.Open(ANSA_FILE)
    if result != 1:
        print("base.Open failed, trying utils.Merge...")
        result = utils.Merge(filename=ANSA_FILE, model_action="overwrite_model")
        if result != 1:
            print("ERROR: Cannot open file!")
            return
    print("File opened successfully.")

    # Step 2: Get current deck
    deck = base.CurrentDeck()
    print("Current deck: {}".format(deck))

    # Step 3: Get all element types and collect all elements
    print("Collecting all elements...")
    element_types = base.TypesInCategory(deck, "__ELEMENTS__")
    if not element_types:
        print("ERROR: No element types found for this deck!")
        return
    print("Element types: {}".format(element_types))

    all_elements = base.CollectEntities(deck, None, element_types, True)
    if not all_elements:
        print("ERROR: No elements found in the model!")
        return
    print("Found {} elements.".format(len(all_elements)))

    # Step 4: Create numbering rule for elements
    print("Creating numbering rule: from {} to {}...".format(RENUMBER_FROM, RENUMBER_TO))
    rule = base.CreateNumberingRuleWithIncrement(
        deck=deck,
        rule_source="TOOL",
        reference_entity=all_elements,
        element_type=None,
        apply_mode="PER_GROUP",
        from_value=RENUMBER_FROM,
        to_value=RENUMBER_TO,
        increment_value=1,
        rule_name="Renumber_Elements",
    )

    if rule is None:
        print("ERROR: Failed to create numbering rule!")
        return
    print("Numbering rule created.")

    # Step 5: Apply the renumber rule
    print("Applying renumber rule...")
    result = base.Renumber(rules=rule)
    print("Renumber completed (result={}).".format(result))

    print("\nDone! Elements renumbered from {} to {}.".format(RENUMBER_FROM, RENUMBER_TO))


if __name__ == "__main__":
    main()
