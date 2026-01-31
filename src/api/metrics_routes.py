"""
Metrics API Blueprint
Provides REST endpoints for querying metrics and analytics.
"""

from flask import Blueprint, jsonify, request

from src.database.connection import get_session
from src.database.queries import QueryHelpers
from src.database.models import Team, Organization, JiraProject
from src.utils.logger import get_logger

logger = get_logger(__name__)

metrics_bp = Blueprint('metrics', __name__, url_prefix='/api/metrics')


@metrics_bp.route('/velocity/<int:team_id>', methods=['GET'])
def get_velocity(team_id: int):
    """
    Get velocity metrics for a team.
    
    Args:
        team_id: Team ID
    
    Query params:
        sprints: Number of sprints to include (default 5)
    
    Returns:
        JSON with velocity data
    """
    try:
        sprint_count = int(request.args.get('sprints', 5))
        
        with get_session() as session:
            queries = QueryHelpers(session)
            
            velocity_data = queries.get_team_velocity(team_id, sprint_count=sprint_count)
            
            # Calculate average
            avg_velocity = 0
            if velocity_data:
                avg_velocity = sum(s.get('velocity', 0) for s in velocity_data) / len(velocity_data)
        
        return jsonify({
            'success': True,
            'team_id': team_id,
            'average_velocity': round(avg_velocity, 2),
            'sprints': velocity_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get velocity for team {team_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/sprint/<int:sprint_id>', methods=['GET'])
def get_sprint_metrics(sprint_id: int):
    """
    Get detailed metrics for a sprint.
    
    Args:
        sprint_id: Sprint ID
    
    Returns:
        JSON with sprint metrics
    """
    try:
        with get_session() as session:
            queries = QueryHelpers(session)
            
            metrics = queries.get_sprint_metrics(sprint_id)
            
            if not metrics:
                return jsonify({
                    'success': False,
                    'error': 'Sprint not found'
                }), 404
        
        return jsonify({
            'success': True,
            'sprint': metrics
        })
        
    except Exception as e:
        logger.error(f"Failed to get sprint metrics for {sprint_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/daily/<int:team_id>', methods=['GET'])
def get_daily_metrics(team_id: int):
    """
    Get daily metrics for a team.
    
    Args:
        team_id: Team ID
    
    Query params:
        days: Number of days to include (default 30)
    
    Returns:
        JSON with daily metrics
    """
    try:
        days = int(request.args.get('days', 30))
        
        with get_session() as session:
            queries = QueryHelpers(session)
            
            daily_data = queries.get_daily_metrics(team_id, days=days)
        
        return jsonify({
            'success': True,
            'team_id': team_id,
            'days': days,
            'metrics': daily_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get daily metrics for team {team_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/priority/<int:team_id>', methods=['GET'])
def get_priority_distribution(team_id: int):
    """
    Get priority distribution for a team.
    
    Args:
        team_id: Team ID
    
    Returns:
        JSON with priority distribution
    """
    try:
        with get_session() as session:
            queries = QueryHelpers(session)
            
            priority_data = queries.get_priority_distribution(team_id)
        
        return jsonify({
            'success': True,
            'team_id': team_id,
            'priorities': priority_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get priority distribution for team {team_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/aging/<int:team_id>', methods=['GET'])
def get_aging(team_id: int):
    """
    Get ticket aging analysis for a team.
    
    Args:
        team_id: Team ID
    
    Returns:
        JSON with aging buckets
    """
    try:
        with get_session() as session:
            queries = QueryHelpers(session)
            
            aging_data = queries.get_ticket_aging(team_id)
        
        return jsonify({
            'success': True,
            'team_id': team_id,
            'aging': aging_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get aging for team {team_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/time-tracking/<int:team_id>', methods=['GET'])
def get_time_tracking(team_id: int):
    """
    Get time tracking summary for a team.
    
    Args:
        team_id: Team ID
    
    Returns:
        JSON with time tracking summary
    """
    try:
        with get_session() as session:
            queries = QueryHelpers(session)
            
            time_data = queries.get_time_tracking_summary(team_id)
        
        return jsonify({
            'success': True,
            'team_id': team_id,
            'time_tracking': time_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get time tracking for team {team_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/kanban/<int:board_id>', methods=['GET'])
def get_kanban_metrics(board_id: int):
    """
    Get Kanban flow metrics for a board.
    
    Args:
        board_id: Board Jira ID
    
    Returns:
        JSON with Kanban flow data
    """
    try:
        with get_session() as session:
            queries = QueryHelpers(session)
            
            flow_data = queries.get_kanban_flow_metrics(board_id)
            swimlane_data = queries.get_swimlane_workload(board_id)
        
        return jsonify({
            'success': True,
            'board_id': board_id,
            'flow': flow_data,
            'swimlanes': swimlane_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get Kanban metrics for board {board_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/labels/<int:project_id>', methods=['GET'])
def get_label_analysis(project_id: int):
    """
    Get label usage analysis for a project.
    
    Args:
        project_id: Project ID
    
    Returns:
        JSON with label analysis
    """
    try:
        with get_session() as session:
            queries = QueryHelpers(session)
            
            label_data = queries.get_label_analysis(project_id)
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'labels': label_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get label analysis for project {project_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/components/<int:project_id>', methods=['GET'])
def get_component_workload(project_id: int):
    """
    Get component workload for a project.
    
    Args:
        project_id: Project ID
    
    Returns:
        JSON with component workload
    """
    try:
        with get_session() as session:
            queries = QueryHelpers(session)
            
            component_data = queries.get_component_workload(project_id)
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'components': component_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get component workload for project {project_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_bp.route('/versions/<int:project_id>', methods=['GET'])
def get_version_progress(project_id: int):
    """
    Get version/release progress for a project.
    
    Args:
        project_id: Project ID
    
    Returns:
        JSON with version progress
    """
    try:
        with get_session() as session:
            queries = QueryHelpers(session)
            
            version_data = queries.get_version_progress(project_id)
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'versions': version_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get version progress for project {project_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
