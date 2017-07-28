def get_canvas_text(x):
    # Join text of nested canvas parts
    t = []
    if isinstance(x, list):
        for y in x:
            t.append(get_canvas_text(y))
    else:
        t.append(x[2].decode('utf-8'))
    return ''.join(t)

