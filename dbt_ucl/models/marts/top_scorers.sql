-- ================================================================
-- Model   : top_scorers
-- Layer   : Gold — Mart
-- Sources : stg_players (fact), stg_teams (dimension)
-- Purpose : UCL top scorer leaderboard.
--           Enriches player stats with team metadata via join.
--           Adds derived analytics metrics: goal_involvement,
--           non_penalty_goals, penalty_pct_of_goals.
-- ================================================================

with players as (
    select * 
    from {{ ref('stg_players') }}
),

teams as (
    select
        team_id,
        team_display_name,
        area_name as team_country,
        venue_name as team_stadium

    from {{ ref('stg_teams') }}
),

enriched as (
    select
        p.scorer_rank,
        p.player_id,
        p.player_name,
        p.nationality,
        p.position,
        p.player_dob,
        p.team_id,
        coalesce(t.team_display_name, p.team_name) as team_name,
        t.team_country,
        t.team_stadium,
        p.team_tla,
        coalesce(p.goals, 0) as goals,
        coalesce(p.assists, 0) as assists,
        coalesce(p.penalties, 0) as penalties_scored,
        coalesce(p.non_penalty_goals, 0) as non_penalty_goals,
        coalesce(p.goals, 0) + coalesce(p.assists, 0) as goal_involvement,
        case
            when coalesce(p.goals, 0) = 0
                then 0.0
            else round(
                cast(coalesce(p.penalties, 0) as float)
                    / coalesce(p.goals, 0) * 100, 1)
        end as penalty_pct_of_goals,
        p.silver_processed_at,
        current_timestamp as gold_created_at

    from players p
    left join teams t on p.team_id = t.team_id
)

select * from enriched
order by scorer_rank