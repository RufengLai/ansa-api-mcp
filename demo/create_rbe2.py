import ansa
from ansa import base
from ansa import constants
import math

# File path
ANSA_FILE = r"D:\claude_space\ansa_test\demo\kunlun_40.03.ansa"

# Master point coordinates
MASTER_X = 3599.972634
MASTER_Y = -847.622000
MASTER_Z = 1235.131882

# Distance threshold for slave nodes
DISTANCE_THRESHOLD = 8.0


def distance_3d(p1, p2):
    return math.sqrt(
        (p1[0] - p2[0]) ** 2
        + (p1[1] - p2[1]) ** 2
        + (p1[2] - p2[2]) ** 2
    )


def main():
    # Step 1: Open the ANSA file
    print("Opening file: {}".format(ANSA_FILE))
    result = base.Open(ANSA_FILE)
    if result != 1:
        print("Failed to open file, trying utils.Merge...")
        from ansa import utils
        result = utils.Merge(filename=ANSA_FILE)
        if result != 1:
            print("ERROR: Cannot open file!")
            return
    print("File opened successfully.")

    # Step 2: Create the master point
    print("Creating master point at ({}, {}, {})".format(MASTER_X, MASTER_Y, MASTER_Z))
    master_point = base.Newpoint(MASTER_X, MASTER_Y, MASTER_Z)
    if master_point is None:
        print("ERROR: Failed to create master point!")
        return
    print("Master point created.")

    # Step 3: Collect all GRID nodes from the model
    print("Collecting all GRID nodes...")
    all_grids = base.CollectEntities(constants.NASTRAN, None, "GRID", True)
    if not all_grids:
        print("ERROR: No GRID nodes found in the model!")
        return
    print("Found {} GRID nodes.".format(len(all_grids)))

    # Step 4: Find grids within distance threshold
    print("Finding grids within {} of master point...".format(DISTANCE_THRESHOLD))
    master_coords = (MASTER_X, MASTER_Y, MASTER_Z)
    slave_node_ids = []

    for grid in all_grids:
        coords = base.GetEntityCardValues(
            constants.NASTRAN, grid, ("X1", "X2", "X3")
        )
        if coords and all(v is not None for v in [coords.get("X1"), coords.get("X2"), coords.get("X3")]):
            try:
                node_coords = (float(coords["X1"]), float(coords["X2"]), float(coords["X3"]))
                dist = distance_3d(master_coords, node_coords)
                if dist < DISTANCE_THRESHOLD:
                    node_id = base.GetEntityCardValues(constants.NASTRAN, grid, ("__id__",))
                    if node_id:
                        slave_node_ids.append(node_id["__id__"])
            except (ValueError, TypeError):
                continue

    print("Found {} slave nodes within distance {}.".format(len(slave_node_ids), DISTANCE_THRESHOLD))

    if not slave_node_ids:
        print("WARNING: No slave nodes found within distance threshold!")
        print("Creating RBE2 with master point only (no slaves).")

    # Step 5: Create RBE2 using BranchEntity
    # First, get the master node ID - we need a GRID node for the master
    # The Newpoint creates a geometry point, we need to find or create a GRID at that location
    # Let's check if there's already a node at the master point location
    master_node = None

    # Search for an existing node at the master point
    nearest = base.NearestNode([[MASTER_X, MASTER_Y, MASTER_Z]], 0.1)
    if nearest and nearest[0] is not None:
        dist_check = distance_3d(
            master_coords,
            tuple(float(v) for v in base.GetEntityCardValues(
                constants.NASTRAN, nearest[0], ("X1", "X2", "X3")
            ).values())
        )
        if dist_check < 0.01:
            master_node = nearest[0]
            print("Found existing node at master point location: ID {}".format(
                base.GetEntityCardValues(constants.NASTRAN, master_node, ("__id__",))["__id__"]
            ))

    if master_node is None:
        # Create a new GRID node at the master point location
        master_node = base.CreateEntity(constants.NASTRAN, "GRID", {
            "X1": MASTER_X,
            "X2": MASTER_Y,
            "X3": MASTER_Z,
        })
        if master_node is None:
            print("ERROR: Failed to create master GRID node!")
            return
        print("Created new master GRID node.")

    # Get master node ID for BranchEntity
    master_id = base.GetEntityCardValues(constants.NASTRAN, master_node, ("__id__",))["__id__"]
    print("Master node ID: {}".format(master_id))

    # Create RBE2: master node first, then slave nodes
    all_node_ids = [master_id] + slave_node_ids

    print("Creating RBE2 with {} nodes (1 master + {} slaves)...".format(
        len(all_node_ids), len(slave_node_ids)
    ))

    rbe2 = base.BranchEntity("RBE2", all_node_ids, "add")
    if rbe2 is None:
        print("ERROR: Failed to create RBE2!")
        return

    rbe2_id = base.GetEntityCardValues(constants.NASTRAN, rbe2, ("__id__",))["__id__"]
    print("RBE2 created successfully! Element ID: {}".format(rbe2_id))
    print("Master node ID: {}".format(master_id))
    print("Slave nodes: {} nodes".format(len(slave_node_ids)))

    print("\nDone!")


if __name__ == "__main__":
    main()
