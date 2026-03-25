from polecat.manager import PolecatManager

manager = PolecatManager()
print(manager.polecats_dir)
print(manager.crew_dir)
print(list(manager.polecats_dir.iterdir()))
