def is_connected(q1, q2, connectivity):
    return [q1, q2] in connectivity or [q2, q1] in connectivity