### Create Fully Connected Graph
```bash
python -m cs4545.system.graphgen gen_graph 10 10  True True
```

### Run Double Spending Algorithm
```bash
python -m cs4545.system.util compose 10 10 topologies/fully_connected_10graph.yaml transaction
sudo docker compose build
sudo docker compose up
```

### Aggregate Output Data

```bash
python -m cs4545.system.aggregate_yml_output
```
