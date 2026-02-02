---
name: schema-exploration
description: For discovering and understanding database structure, tables, columns, and relationships
---

# Schema Exploration Skill (Restaurant Management)

## When to Use This Skill

Use this skill when you need to:
- Understand the database structure
- Find which tables contain certain types of data
- Discover column names and data types
- Map relationships between tables
- Answer questions like "What tables are available?" or "What columns does the Customer table have?"

## Workflow

### 1. List All Tables
Use `sql_db_list_tables` tool to see all available tables in the database.

This returns the complete list of tables you can query.

### 2. Get Schema for Specific Tables
Use `sql_db_schema` tool with table names to examine:
- **Column names** - What fields are available
- **Data types** - INTEGER, TEXT, DATETIME, etc.
- **Sample data** - 3 example rows to understand content
- **Primary keys** - Unique identifiers for rows
- **Foreign keys** - Relationships to other tables

### 3. Map Relationships
Identify how tables connect:
- Look for columns ending in `_id` (e.g., order_id, branch_id)
- Foreign keys link to primary keys in other tables
- Document parent-child relationships

### 4. Answer the Question
Provide clear information about:
- Available tables and their purpose
- Column names and what they contain
- How tables relate to each other
- Sample data to illustrate content

## Example: "What tables are available?"

**Step 1:** Use `sql_db_list_tables`

**Response:**
```
Key table groups in this restaurant system include:
1. Orders and items - orders, order_items, order_item_modifiers
2. Dining and tables - dining_sessions, restaurant_tables, table_transfers
3. Payments and POS - payments, payment_methods, register_sessions
4. Menu and modifiers - menu, modifier_groups, modifier_options
5. Inventory and procurement - stock_levels, stock_movements, purchase_orders, purchase_order_lines, warehouses
6. People and org - customers, staff, branches, franchises
```

## Example: "What columns does the Orders table have?"

**Step 1:** Use `sql_db_schema` with table name "orders"

**Response:**
```
The orders table typically includes:

- id (UUID) - Primary key
- branch_id (UUID) - Branch location
- dining_session_id (UUID) - Dining session (if in-store)
- status (TEXT) - Order status
- total_amount (NUMERIC) - Order total
- tax_amount (NUMERIC) - Tax total
- created_at (TIMESTAMP) - When the order was created
- completed_at (TIMESTAMP) - When the order was completed
```

## Example: "How do I find revenue by menu item?"

**Step 1:** Identify tables needed
- menu (item names)
- order_items (item quantities and prices)
- orders (timestamps and order status)

**Step 2:** Map relationships
```
menu (id)
  ↓ 1:many
order_items (item_id, order_id, quantity, base_price)
  ↓ many:1
orders (id, created_at, status)
```

**Response:**
```
To find revenue by menu item, you'll need to:
1. Start with the menu table
2. JOIN to order_items on menu.id = order_items.item_id
3. JOIN to orders on order_items.order_id = orders.id
4. SUM revenue (quantity * base_price)
5. GROUP BY menu item name

This requires the query-writing skill to execute.
```

## Quality Guidelines

**For "list tables" questions:**
- Show all table names
- Add brief descriptions of what each contains
- Group related tables (e.g., music catalog, transactions, people)

**For "describe table" questions:**
- List all columns with data types
- Explain what each column contains
- Show sample data for context
- Note primary and foreign keys
- Explain relationships to other tables

**For "how do I query X" questions:**
- Identify required tables
- Map the JOIN path
- Explain the relationship chain
- Suggest next steps (use query-writing skill)

## Common Exploration Patterns

### Pattern 1: Find a Table
"Which table has customer information?"
→ Use list_tables, then describe Customer table

### Pattern 2: Understand Structure
"What's in the Invoice table?"
→ Use schema tool to show columns and sample data

### Pattern 3: Map Relationships
"How are artists connected to sales?"
→ Trace the foreign key chain: Artist → Album → Track → InvoiceLine → Invoice

## Tips

- Table names are mostly lowercase snake_case and often plural (orders, order_items, payments)
- Some tables are singular (menu), so check names via list_tables first
- Foreign keys typically use `_id` suffix and match a parent table's primary key
- Use sample data to confirm value formats (status codes, timestamps, enums)
- When unsure which table to use, list all tables first
