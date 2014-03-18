GRANT ALL ON spatial_ref_sys TO {{ dbname }};
GRANT ALL ON geometry_columns TO {{ dbname }};
ALTER FUNCTION cleanGeometry(geometry) OWNER TO {{ dbname }};
