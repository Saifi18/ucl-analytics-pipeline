-- ================================================================
-- Model   : stg_players
-- Layer   : Staging
-- Source  : data/silver_local/players_silver_ucl_players_*.parquet
-- Purpose : UCL top scorers staging.
--           Source for top_scorers mart model.
-- ================================================================

with source as (

    select *
    from read_parquet('../data/silver_local/players_silver_ucl_players_*.parquet')

),

staged as (

    select
        --Scorer rank from Silver 
        scorer_rank,

        --Player identifiers 
        player_id,
        player_name,
        player_first_name,
        player_last_name,
        player_dob,
        nationality,
        position,
        shirt_number,

        --Team context 
        team_id,
        team_name,
        team_short_name,
        team_tla,

        --Scoring stats 
        goals,
        assists,
        penalties,
        non_penalty_goals,

        --metadata 
        silver_processed_at,
        source_blob

    from source

)

select * from staged