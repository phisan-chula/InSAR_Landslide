# InSAR_Landslide

```
python3 1_Extract_SAFE.py -h
usage: 1_Extract_SAFE.py [-h] [-d] TOML

positional arguments:
  TOML        TOML config file

options:
  -h, --help  show this help message and exit
  -d, --dump  dump nodes and edges for each component(s)
```


```
python3 2_Plot_SBAS.py -h
usage: 2_Plot_SBAS.py [-h] [-x] [-d] TOML

positional arguments:
  TOML            TOML config file

options:
  -h, --help      show this help message and exit
  -x, --networkx  plot networkX graph(s)
  -d, --dump      dump nodes and edges for each component(s)
```


```
 python3 3_ts_Analysis.py -h
usage: 3_ts_Analysis.py [-h] [-c] [-p] TOML

positional arguments:
  TOML           TOML config file

options:
  -h, --help     show this help message and exit
  -c, --clip     clip dataset as DEM for MintPy processging
  -p, --process  do process MintPy
```
