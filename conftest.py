
def pytest_addoption(parser):
    parser.addoption("--clients", action="store", default=2, type=int)
