DATA_DIR=../data
python manage.py import_planning_units \
    $DATA_DIR/planning_units_simple.shp \
    $DATA_DIR/metrics.xls 
    #$DATA_DIR/planning_units_full.shp

