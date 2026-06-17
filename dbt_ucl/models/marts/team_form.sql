-- ================================================================
-- Model   : team_form
-- Layer   : Gold — Mart
-- Source  : stg_matches
-- Purpose : Current form per UCL team.
--           Shows points, goals, and GD from last 5 matches
--           plus cumulative season totals.
-- Pattern : UNION ALL + window frames for rolling calculations
-- ================================================================

with finished_matches as (

    select *
    from {{ ref('stg_matches') }}
    where is_finished = true

),
--Step 1: One row per team per match
team_match_records as (

    -- Home team perspective
    select
        home_team_id as team_id,
        home_team_name as team_name,
        match_date,
        match_id,
        home_result as result,
        coalesce(home_score_ft, 0) as goals_scored,
        coalesce(away_score_ft, 0) as goals_conceded,
        case
            when home_result = 'W' then 3
            when home_result = 'D' then 1
            else 0
        end as points_earned

    from finished_matches

    union all

    -- Away team perspective
    select
        away_team_id as team_id,
        away_team_name as team_name,
        match_date,
        match_id,
        -- Flip the result for the away team
        case
            when home_result = 'W' then 'L'
            when home_result = 'L' then 'W'
            else 'D'
        end as result,
        coalesce(away_score_ft, 0) as goals_scored,
        coalesce(home_score_ft, 0) as goals_conceded,
        case
            when home_result = 'L' then 3
            when home_result = 'D' then 1
            else 0
        end as points_earned

    from finished_matches

),

--Step 2: Number each team's matches chronologically

numbered_records as (

    select*, row_number() over ( partition by team_id order by match_date asc, match_id asc ) as match_number
    from team_match_records

),

--Step 3: Apply rolling window calculations
with_rolling_stats as (

    select
        team_id,
        team_name,
        match_date,
        match_id,
        match_number,
        result,
        goals_scored,
        goals_conceded,
        points_earned,

        -- Rolling points (last 5 matches) 
        sum(points_earned) over (
            partition by team_id
            order by match_date asc, match_id asc
            rows between 4 preceding and current row
        ) as points_last_5,

        --Rolling goals scored (last 5) 
        sum(goals_scored) over (
            partition by team_id
            order by match_date asc, match_id asc
            rows between 4 preceding and current row
        ) as goals_scored_last_5,

        --Rolling goals conceded (last 5) 
        sum(goals_conceded) over (
            partition by team_id
            order by match_date asc, match_id asc
            rows between 4 preceding and current row
        ) as goals_conceded_last_5,

        -- Cumulative season points 
        sum(points_earned) over (
            partition by team_id
            order by match_date asc, match_id asc
            rows between unbounded preceding and current row
        ) as cumulative_points,

        --Cumulative matches played
        count(match_id) over (
            partition by team_id
            order by match_date asc, match_id asc
            rows between unbounded preceding and current row
        ) as cumulative_played

    from numbered_records

),

--Step 4: Keep only the most recent match per team

latest_per_team as (

    select
        team_id,
        max(match_number) as latest_match_number
    from with_rolling_stats
    group by team_id

),

-- Step 5: Final form table

final as (

    select
        rs.team_id,
        rs.team_name,
        rs.match_date as last_match_date,
        rs.cumulative_played as matches_played,
        rs.cumulative_points as total_points,
        rs.points_last_5,
        rs.goals_scored_last_5,
        rs.goals_conceded_last_5,

        -- Goal difference in last 5 matches
        rs.goals_scored_last_5
            - rs.goals_conceded_last_5 as gd_last_5,

        -- Form label based on last 5 points
        case
            when rs.points_last_5 >= 10 then 'Good'
            when rs.points_last_5 >= 5  then 'Average'
            else 'Poor'
        end as form_label,

        current_timestamp as gold_created_at

    from with_rolling_stats rs
    inner join latest_per_team lp
        on  rs.team_id      = lp.team_id
        and rs.match_number = lp.latest_match_number

)

-- Order by form — best form teams first 
select * from final
order by points_last_5 desc, gd_last_5 desc