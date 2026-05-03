


def transpilation_tracker(pass_, dag, time, property_set, count):
        # Get the name of the pass
        pass_name = pass_.name()
        
        # Print the progress
        print(f"Step {count:03d} | {pass_name:<30} | Time: {time:.4f}s | Gate Count: {dag.count_ops()}")