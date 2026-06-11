-- ================================================================
-- Model   : ucl_standings
-- Layer   : Gold — Mart
-- Source  : stg_matches
-- Purpose : Full UCL standings table.
--           Calculates P W D L GF GA GD Pts per team.
-- Pattern : UNION ALL — one match produces two rows (home + away)
--           then aggregate per team to get season totals.
-- ================================================================

with finished_matches as (
    -- only finished matches
    select * 
    from {{ref('stg_matches')}} 
    where is_finished = true
),

-- Step 1: Home team row per match 
-- We calculate points earned from the home team's perspective
home_records as (

    select
        home_team_id as team_id,
        home_team_name as team_name,
        home_team_short as team_short,

        1 as played,

        case 
            when home_result = 'W' then 1
            else 0
        end as won,

        case
            when home_result = 'D' then 1
            else 0
        end as drawn,

        case
            when home_result = 'L' then 1
            else 0
        end as lost,

        coalesce(home_score_ft, 0) as goals_for,

        coalesce(away_score_ft, 0) as goals_against,

        case
            when home_result = 'W' then 3
            when home_result = 'D' then 1
            else 0
        end as points_earned

    from finished_matches

),

-- Step 2: Away team row per match 
-- We calculate points earned from the away team's perspective
away_records as (

    select
        away_team_id as team_id,
        away_team_name as team_name,
        away_team_short as team_short,
        1 as played,

        case
            when home_result = 'L' then 1
            else 0
        end as won,

        case
            when home_result = 'D' then 1
            else 0
        end as drawn,

        case
            when home_result = 'W' then 1
            else 0
        end as lost,

        -- Away team's goals scored = away_score_ft
        coalesce(away_score_ft, 0) as goals_for,

        -- Away team's goals conceded = home_score_ft
        coalesce(home_score_ft, 0) as goals_against,

        case
            when home_result = 'L' then 3
            when home_result = 'D' then 1
            else 0
        end as points_earned

    from finished_matches

),

-- Step 3: Combine home and away into one dataset 
all_team_match_records as (

    select * from home_records
    union all
    select * from away_records

),

-- Step 4: Aggregate per team 
team_season_totals as (

    select
        team_id,
        team_name,
        team_short,
        sum(played) as played,
        sum(won) as won,
        sum(drawn) as drawn,
        sum(lost) as lost,
        sum(goals_for) as goals_for,
        sum(goals_against) as goals_against,
        sum(goals_for) - sum(goals_against) as goal_difference,
        sum(points_earned)  as points

    from all_team_match_records
    group by team_id, team_name, team_short
),

-- Step 5: Add position and derived metrics 
final as (

    select
        row_number() over (
            order by
                points           desc,
                goal_difference  desc,
                goals_for        desc
        ) as position,

        team_id,
        team_name,
        team_short,
        played,
        won,
        drawn,
        lost,
        goals_for,
        goals_against,
        goal_difference,
        points,

        -- Win percentage — how often this team wins
        -- nullif prevents division by zero if played = 0
        round(
            cast(won as float)
                / nullif(played, 0) * 100, 1
        ) as win_pct,

        -- Points per game — normalised performance metric
        round(
            cast(points as float)
                / nullif(played, 0),2
        ) as points_per_game,

        current_timestamp as gold_created_at

    from team_season_totals

)

select * from final
order by position

