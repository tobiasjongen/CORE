# CORE: a Complex Event Recognition Engine

## Overview

This is a C++ reimplementation of the CORE engine, as presented in the paper ["CORE: a Complex Event Recognition Engine"](https://www.vldb.org/pvldb/vol15/p1951-riveros.pdf) by Marco Bucchi, Alejandro Grez, Andrés Quintana, Cristian Riveros, and Stijn Vansummeren. This engine is designed for the efficient evaluation of complex event queries over large data streams in real time.

## Features

- **Efficient Query Evaluation**: Specialized in evaluating a broad array of complex event queries, including those featuring the 'within time' operator.
  
- **Automaton-based Algorithm**: Utilizes an innovative automaton-based evaluation algorithm that maintains a data structure to represent the set of partial matches in constant time per input event.

- **Stable Performance**: Exhibits consistent performance regardless of query size or time window size.

- **High Scalability**: Aims to outperform state-of-the-art CER systems across multiple workloads.

- **Test Driven Development**: Developed using unit tests with the Catch2 framework.

- **Conan Package Manager**

## Quick Start

To get started quickly in your local machine: 

```bash
# Clone the repository
git clone https://github.com/CER-CORE/CORE

# Navigate into the directory
cd CORE

# Compile the project and run third party and unit tests
./scripts/build_and_test.sh

```
You can also use Docker. The image contains the compiled engine and the `pycer` Python bindings, but not the source tree or the example datasets, so mount the repository into the container:

```bash
# Build the image (compiles the engine and runs the tests)
docker compose build

# Start a terminal in the container with the repository mounted at /work
docker compose run --rm -v "$PWD":/work core-terminal bash
```

On systems with SELinux (e.g. Fedora), append `:z` to the volume (`"$PWD":/work:z`) if you get permission errors.

Following the local steps you will be building the project in Debug mode. There are other build options, which are Release, RelWithDebInfo and MinSizeRel:

```bash
./scripts/build_and_test.sh -b Release

./scripts/build_and_test.sh -b RelWithDebInfo

./scripts/build_and_test.sh -b MinSizeRel
```

For more detailed installation and setup instructions, including manual installation steps, please refer to our [Installation Guide](docs/users/INSTALLATION.md).

## Stream Declaration

If a user wants to connect a stream to CORE he has to declare the stream that is going to connect. In order to declare the stream, the client has to specify the name of the stream, the events that this stream has and the attributes (with its specific type) of each event. Here is an example:  

```bash
"CREATE STREAM StreamName {\n"
"EVENT EventName { AttributeName:AttributeType, Value1:string, Value2:boolean },\n"
"EVENT Hum { ID:int, Value3:double },\n"
"EVENT Hum2 { ID:int }\n"
"}";
```

The types of attributes that are available are int, string, double and bool.

One feature that CORE supports is that it allows multiple streams to share events. For that, the event must have the same name in every stream that is declared.

## Running CORE

CORE is used through its Python bindings, `pycer`. In the Docker image they are already installed. To use them locally, set up these four things once, from the repository root:

1. **uv**, the Python package manager that builds and runs `pycer`: see https://docs.astral.sh/uv/
2. **Ninja**, the build tool CMake uses: `sudo apt-get install ninja-build` (Fedora: `sudo dnf install ninja-build`)
3. **vcpkg and the C++ dependencies**: `./scripts/install_dependencies.sh` clones and bootstraps vcpkg into `vcpkg/` and generates the ANTLR parser files. Without this step the build fails with `Could not find toolchain file: .../vcpkg/scripts/buildsystems/vcpkg.cmake`.
4. **pycer**: `./scripts/build_pycer.sh` compiles the engine and installs the bindings into `.venv`. The first build takes a while because vcpkg compiles all dependencies from source. Afterwards, run the Python commands below with `.venv/bin/python` (or after `source .venv/bin/activate`). `uv run` also works, but it may rebuild `pycer` first.

If you move or re-clone the repository, delete `build/` before running `scripts/build.sh` again, because its CMake cache stores the old vcpkg path.

### Offline

In offline mode a single process feeds a whole data file through the engine and prints all matches. `run_query.py` does this for a query, a stream declaration and a CSV file:

```bash
python run_query.py <query.txt> <declaration.core> <data.csv> [options.core] \
    [--output output/matches.csv] [--id-attribute id]
```

Run it from the repository root (in the Docker container: `cd /work`). Query, declaration and data file are required; the options file is optional. The smallest predefined example is the crypto market dataset, which has two events:

```bash
python run_query.py src/targets/experiments/crypto_market/queries/q1.txt \
    src/targets/experiments/crypto_market/declaration.core \
    src/targets/experiments/crypto_market/crypto_market_data.csv
```

Each output line is one match: the time span `[start,end]`, followed by the matched events with their event type `id` and attributes in declaration order. Datasets that deliver events out of order (`unordered_stocks`, `ordered_bluesky`, `unordered_bluesky`) also need their `quarantine_declaration.core` as fourth argument.

With `--output output/matches.csv` the matches are written to a CSV file instead of printed: one line per match, containing the value of one attribute of each matched event, comma-separated in match order. `--id-attribute` picks that attribute (default `id`); every event type in a match must have it. Keep result files in `output/` at the repository root; missing folders are created.

In your own code, the offline flow looks like this:

```python
server = pycer.PyOfflineServer()
stream_info = server.declare_stream(declaration)
server.add_query(query)
server.send_events(events)  # list of pycer.PyEvent
print(server.get_output())
```

### Online

In online mode the engine runs as a long-lived server. Streamers send events to it, and clients add queries at runtime and receive matches as they happen; all parts communicate over ZeroMQ. `docker-compose.online.yml` runs each part in its own container:

| Service | Component | Purpose |
|---------|-----------|---------|
| `core-engine` | `pycer.PyOnlineServer` | The engine (router `:5000`, stream listener `:5001`, query results `:5002+`) |
| `core-api` | `core_server_py` | REST API to manage streams and queries, websocket per query for results, on `http://localhost:8000` |
| `streamer` | `python_streamer` | Forwards live Coinbase ticker and Bluesky events to the engine and declares their streams |

```bash
# Build the base image first (only needed once, or after engine changes)
docker compose build

# Start engine, API and streamer
docker compose -f docker-compose.online.yml up --build
```

Once the streamer has declared its streams, interact with the engine through the API:

```bash
# List the declared streams
curl localhost:8000/all-streams-info

# Add a query; the response is the query ID
curl -X POST localhost:8000/add-query -H 'content-type: application/json' \
  -d "{\"query\": \"SELECT * FROM TICKER WHERE Buy FILTER Buy[product_id = 'BTC-USD']\", \"query_name\": \"btc\"}"

# Receive matches for query 0 as JSON (e.g. with websocat)
websocat ws://localhost:8000/0

## alternatively
curl --no-buffer ws://localhost:8000/0

# Deactivate query 0
curl -X DELETE localhost:8000/inactivate-query/0
```

The engine keeps streams and queries in memory, so they have to be added again after it restarts. To connect your own data source, add a streamer to `python_streamer/` modeled on `coinbase/ticker.py`; `main.py` reads the engine address from `CORE_HOST`, `CORE_ROUTER_PORT` and `CORE_STREAM_PORT`.

## Experiments

The datasets used for experiments can be found in `src/targets/experiments`. Each dataset has its own data, stream declaration, queries and expected results for every query.

Integration tests run all experiments via the Python bindings (`pycer`), comparing output against expected results:

```bash
uv run pytest tests/e2e/ -v --server-mode offline
```

With `--server-mode online` the queries run through the ZeroMQ server instead; those tests only check that nothing crashes.

## Detailed Documentation

For comprehensive documentation:

- **Users**: Navigate to [User Documentation](./docs/users/README.md). (Documentation in development)
  
- **Developers**: Navigate to [Developer Documentation](./docs/developers/README.md).

## Related Work

- The original paper can be found [here](https://www.vldb.org/pvldb/vol15/p1951-riveros.pdf).

## Contributing

Contributions are welcome! See our [Contributing's Guide](docs/users/CONTRIBUTING.md) for details.

## License

[GNU GENERAL PUBLIC LICENSE](./LICENSE.txt)

## Contact

For additional details or feedback, feel free to [create an issue](https://github.com/CER-CORE/CORE/issues).
