IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.brand') AND name = 'ux_brand_slug'
)
    CREATE UNIQUE INDEX ux_brand_slug ON dbo.brand(slug) WHERE slug IS NOT NULL;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.brand') AND name = 'ux_brand_catalog_slug'
)
    CREATE UNIQUE INDEX ux_brand_catalog_slug ON dbo.brand(catalog_slug)
        WHERE catalog_slug IS NOT NULL;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.categories') AND name = 'ux_categories_slug'
)
    CREATE UNIQUE INDEX ux_categories_slug ON dbo.categories(slug) WHERE slug IS NOT NULL;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.categories') AND name = 'ix_categories_parent_filterable'
)
    CREATE INDEX ix_categories_parent_filterable
        ON dbo.categories(parent_id, is_filterable, name);
