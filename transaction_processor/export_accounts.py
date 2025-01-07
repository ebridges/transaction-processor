from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

query = '''
WITH RECURSIVE account_hierarchy AS (
    --------------------------------------------------------------------
    -- 1) Anchor: Start with root accounts (parent_guid IS NULL)
    --------------------------------------------------------------------
    SELECT
        guid,

        -- Append '0' if code < 5 chars
        CASE WHEN length(code) < 5 THEN code || '0' ELSE code END AS child_code,

        -- Root's fullname is just its own name (no parent)
        name AS fullname,

        -- The row’s own name and code
        name AS name,
        code AS code,

        parent_guid,

        -- No parent for a root
        NULL AS parent_name,
        NULL AS parent_code
    FROM accounts
    WHERE parent_guid IS NULL

    UNION ALL

    --------------------------------------------------------------------
    -- 2) Recursive member:
    -- For each child, join it to the parent row from account_hierarchy
    --------------------------------------------------------------------
    SELECT
        child.guid,

        -- Append '0' if child's code < 5 chars
        CASE WHEN length(child.code) < 5 THEN child.code || '0' ELSE child.code END AS child_code,

        -- Build a deeper fullname by appending the child's name
        parent.fullname || ':' || child.name AS fullname,

        -- The child's own name/code
        child.name,
        child.code,

        child.parent_guid,

        -- The parent's name/code come from the parent row in the CTE
        parent.name AS parent_name,
        parent.code AS parent_code

    FROM accounts AS child
    JOIN account_hierarchy AS parent ON child.parent_guid = parent.guid
)
--------------------------------------------------------------------
-- 3) Final SELECT
--------------------------------------------------------------------
SELECT
    -- The child code from the CTE (already has '0' appended if short)
    account_hierarchy.child_code,

    -- The full hierarchical path (e.g., "grandparent:parent:child")
    account_hierarchy.fullname,

    -- Child’s name
    account_hierarchy.name,

    -- Parent’s name
    account_hierarchy.parent_name,

    -- Append '0' to the parent's code if short (if parent_code is NULL, just returns NULL)
    CASE
      WHEN parent_code IS NOT NULL AND length(parent_code) < 5
      THEN parent_code || '0'
      ELSE parent_code
    END AS parent_code,

    -- Remaining columns come directly from the child's row
    a.account_type,
    a.description,
    a.hidden,
    a.placeholder

FROM account_hierarchy
JOIN accounts AS a ON account_hierarchy.guid = a.guid

-- Exclude any accounts where hidden = 1
WHERE a.hidden <> 1

-- Order by child_code as an integer
ORDER BY CAST(account_hierarchy.child_code AS INTEGER) ASC;
'''


def export_gnucash_accounts(db_url: str) -> list:
    engine = create_engine(db_url, echo=False)
    accounts = []
    with Session(engine) as session:

        sql_query = text(query)

        result = session.execute(sql_query)

        accounts.append(
            'account_code',
            'fullname',
            'name',
            'parent_name',
            'parent_code',
            'account_type',
            'description',
            'hidden',
            'placeholder',
        )

        for row in result:
            fullname = row.fullname.removeprefix('Root Account:')
            accounts.append(
                row.child_code,
                fullname,
                row.name,
                row.parent_name,
                row.parent_code,
                row.account_type,
                row.description,
                row.hidden,
                row.placeholder,
            )
        return accounts
