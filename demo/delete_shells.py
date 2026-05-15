import ansa
from ansa import base
from ansa import utils
from ansa import constants

def main():
    # Step 1: Open the ANSA file
    file_path = r"D:\claude_space\ansa_test\demo\kunlun_40.03.ansa"
    result = utils.Merge(file_path)
    if not result:
        print(f"ERROR: Failed to open file: {file_path}")
        return
    print(f"Successfully opened: {file_path}")

    # Step 2: Collect all shell elements from the current deck
    deck = base.CurrentDeck()
    all_shells = base.CollectEntities(deck, None, "SHELL", filter_visible=False)

    if not all_shells:
        print("No shell elements found in the model.")
        return

    print(f"Total shell elements found: {len(all_shells)}")

    # Step 3: Filter shells with ID < 456
    shells_to_delete = []
    for shell in all_shells:
        vals = base.GetEntityCardValues(deck, shell, ("__id__",))
        shell_id = vals.get("__id__", None)
        if shell_id is not None and shell_id < 456:
            shells_to_delete.append(shell)

    if not shells_to_delete:
        print("No shell elements with ID < 456 found.")
        return

    print(f"Shell elements with ID < 456: {len(shells_to_delete)}")

    # Step 4: Delete the filtered shells
    count = 0
    for shell in shells_to_delete:
        vals = base.GetEntityCardValues(deck, shell, ("__id__",))
        shell_id = vals.get("__id__", "Unknown")
        base.DeleteEntity(shell)
        print(f"  Deleted shell ID: {shell_id}")
        count += 1

    print(f"\nDone! Deleted {count} shell elements.")

if __name__ == "__main__":
    main()
