-- Create receipt_line_items table
CREATE TABLE IF NOT EXISTS receipt_line_items (
    id SERIAL PRIMARY KEY,
    receipt_upload_id INTEGER NOT NULL REFERENCES receipt_uploads(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL DEFAULT 0,
    item_name VARCHAR(500) NOT NULL,
    quantity NUMERIC(10, 3) NOT NULL DEFAULT 1,
    unit_price NUMERIC(12, 2) NOT NULL,
    total_price NUMERIC(12, 2) NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_receipt_line_items_receipt ON receipt_line_items(receipt_upload_id);
CREATE INDEX IF NOT EXISTS ix_receipt_line_items_category ON receipt_line_items(category_id);
