import csv, os, subprocess, tempfile

CASES = [
    ("id,region,amount\n1,north,10.10\n2,south,5\n3,north,0.20\n4,south,\n5,east,abc\n6,east,7.5\n",
     [["north", "10.30"], ["east", "7.50"], ["south", "5.00"]]),
    ("amount,region\n0.10,a\n0.20,a\n0.30,b\n0.30,c\n",
     [["a", "0.30"], ["b", "0.30"], ["c", "0.30"]]),
    ('region,note,amount\n"Smith, Jones",x,3.25\n"Smith, Jones",y,1.75\nZed,"a,b",5.00\n',
     [["Smith, Jones", "5.00"], ["Zed", "5.00"]]),
    ("region,amount\nonly,nan\nonly,1.005\nneg,-2\nonly,inf\nhalf, 0.015 \nhalf,\n",
     [["only", "1.00"], ["half", "0.02"], ["neg", "-2.00"]]),
    ("region,amount\nr,0.005\nr,0.005\nq,0.025\np,0.035\n",
     [["p", "0.04"], ["q", "0.02"], ["r", "0.01"]]),
]
with tempfile.TemporaryDirectory() as d:
    for i, (text, want) in enumerate(CASES):
        a, b = os.path.join(d, f"i{i}.csv"), os.path.join(d, f"o{i}.csv")
        with open(a, "w", newline="") as f:
            f.write(text)
        subprocess.run(["python3", "/app/aggregate.py", a, b], check=True, timeout=30)
        with open(b, newline="") as f:
            rows = list(csv.reader(f))
        assert rows[0] == ["region", "total"], rows
        assert rows[1:] == want, (i, rows[1:], want)
print("ok")
