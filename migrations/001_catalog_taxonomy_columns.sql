IF COL_LENGTH('dbo.brand', 'slug') IS NULL
    ALTER TABLE dbo.brand ADD slug VARCHAR(120) NULL;

IF COL_LENGTH('dbo.brand', 'catalog_slug') IS NULL
    ALTER TABLE dbo.brand ADD catalog_slug VARCHAR(140) NULL;

IF COL_LENGTH('dbo.brand', 'source') IS NULL
    ALTER TABLE dbo.brand ADD source VARCHAR(30) NOT NULL
        CONSTRAINT DF_brand_source DEFAULT ('existing');

IF COL_LENGTH('dbo.categories', 'slug') IS NULL
    ALTER TABLE dbo.categories ADD slug VARCHAR(140) NULL;

IF COL_LENGTH('dbo.categories', 'source') IS NULL
    ALTER TABLE dbo.categories ADD source VARCHAR(30) NOT NULL
        CONSTRAINT DF_categories_source DEFAULT ('existing');

IF COL_LENGTH('dbo.categories', 'is_filterable') IS NULL
    ALTER TABLE dbo.categories ADD is_filterable BIT NOT NULL
        CONSTRAINT DF_categories_is_filterable DEFAULT (1);
