"""
Chart Generation Module
Provides utilities for creating Excel charts using openpyxl.
"""

from typing import Any, Dict, List, Optional, Tuple

from openpyxl.chart import (
    BarChart, LineChart, PieChart, AreaChart, Reference, Series
)
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.layout import Layout, ManualLayout
from openpyxl.worksheet.worksheet import Worksheet

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ChartBuilder:
    """Factory for creating various chart types."""
    
    # Chart style presets
    STYLES = {
        'default': 10,
        'colorful': 11,
        'dark': 12,
        'gradient': 13,
        'professional': 26
    }
    
    @staticmethod
    def create_bar_chart(
        ws: Worksheet,
        data_range: Tuple[int, int, int, int],  # (min_col, min_row, max_col, max_row)
        categories_range: Tuple[int, int, int, int],
        title: str = None,
        x_title: str = None,
        y_title: str = None,
        style: str = 'professional',
        stacked: bool = False,
        horizontal: bool = False
    ) -> BarChart:
        """
        Create a bar chart.
        
        Args:
            ws: Worksheet containing data
            data_range: (min_col, min_row, max_col, max_row) for data
            categories_range: (min_col, min_row, max_col, max_row) for categories
            title: Chart title
            x_title: X-axis title
            y_title: Y-axis title
            style: Chart style preset
            stacked: If True, create stacked chart
            horizontal: If True, create horizontal bars
            
        Returns:
            Configured BarChart object
        """
        chart = BarChart()
        chart.type = "bar" if horizontal else "col"
        chart.style = ChartBuilder.STYLES.get(style, 10)
        
        if stacked:
            chart.grouping = "stacked"
            chart.overlap = 100
        
        if title:
            chart.title = title
        if x_title:
            chart.x_axis.title = x_title
        if y_title:
            chart.y_axis.title = y_title
        
        # Add data
        data = Reference(ws, 
                        min_col=data_range[0], min_row=data_range[1],
                        max_col=data_range[2], max_row=data_range[3])
        categories = Reference(ws,
                              min_col=categories_range[0], min_row=categories_range[1],
                              max_col=categories_range[2], max_row=categories_range[3])
        
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categories)
        
        # Set size
        chart.width = 15
        chart.height = 10
        
        return chart
    
    @staticmethod
    def create_line_chart(
        ws: Worksheet,
        data_range: Tuple[int, int, int, int],
        categories_range: Tuple[int, int, int, int],
        title: str = None,
        x_title: str = None,
        y_title: str = None,
        style: str = 'professional',
        smooth: bool = True
    ) -> LineChart:
        """
        Create a line chart.
        
        Args:
            ws: Worksheet containing data
            data_range: (min_col, min_row, max_col, max_row) for data
            categories_range: (min_col, min_row, max_col, max_row) for categories
            title: Chart title
            x_title: X-axis title
            y_title: Y-axis title
            style: Chart style preset
            smooth: If True, use smooth lines
            
        Returns:
            Configured LineChart object
        """
        chart = LineChart()
        chart.style = ChartBuilder.STYLES.get(style, 10)
        
        if title:
            chart.title = title
        if x_title:
            chart.x_axis.title = x_title
        if y_title:
            chart.y_axis.title = y_title
        
        # Add data
        data = Reference(ws,
                        min_col=data_range[0], min_row=data_range[1],
                        max_col=data_range[2], max_row=data_range[3])
        categories = Reference(ws,
                              min_col=categories_range[0], min_row=categories_range[1],
                              max_col=categories_range[2], max_row=categories_range[3])
        
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categories)
        
        # Apply smooth lines if requested
        if smooth:
            for series in chart.series:
                series.smooth = True
        
        # Set size
        chart.width = 15
        chart.height = 10
        
        return chart
    
    @staticmethod
    def create_pie_chart(
        ws: Worksheet,
        data_range: Tuple[int, int, int, int],
        categories_range: Tuple[int, int, int, int],
        title: str = None,
        style: str = 'colorful'
    ) -> PieChart:
        """
        Create a pie chart.
        
        Args:
            ws: Worksheet containing data
            data_range: (min_col, min_row, max_col, max_row) for data
            categories_range: (min_col, min_row, max_col, max_row) for categories
            title: Chart title
            style: Chart style preset
            
        Returns:
            Configured PieChart object
        """
        chart = PieChart()
        chart.style = ChartBuilder.STYLES.get(style, 11)
        
        if title:
            chart.title = title
        
        # Add data
        data = Reference(ws,
                        min_col=data_range[0], min_row=data_range[1],
                        max_col=data_range[2], max_row=data_range[3])
        categories = Reference(ws,
                              min_col=categories_range[0], min_row=categories_range[1],
                              max_col=categories_range[2], max_row=categories_range[3])
        
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categories)
        
        # Show data labels with percentages
        chart.dataLabels = DataLabelList()
        chart.dataLabels.showPercent = True
        chart.dataLabels.showVal = False
        chart.dataLabels.showCatName = True
        
        # Set size
        chart.width = 12
        chart.height = 10
        
        return chart
    
    @staticmethod
    def create_area_chart(
        ws: Worksheet,
        data_range: Tuple[int, int, int, int],
        categories_range: Tuple[int, int, int, int],
        title: str = None,
        x_title: str = None,
        y_title: str = None,
        style: str = 'professional',
        stacked: bool = False
    ) -> AreaChart:
        """
        Create an area chart (useful for burndown).
        
        Args:
            ws: Worksheet containing data
            data_range: (min_col, min_row, max_col, max_row) for data
            categories_range: (min_col, min_row, max_col, max_row) for categories
            title: Chart title
            x_title: X-axis title
            y_title: Y-axis title
            style: Chart style preset
            stacked: If True, create stacked chart
            
        Returns:
            Configured AreaChart object
        """
        chart = AreaChart()
        chart.style = ChartBuilder.STYLES.get(style, 10)
        
        if stacked:
            chart.grouping = "stacked"
        
        if title:
            chart.title = title
        if x_title:
            chart.x_axis.title = x_title
        if y_title:
            chart.y_axis.title = y_title
        
        # Add data
        data = Reference(ws,
                        min_col=data_range[0], min_row=data_range[1],
                        max_col=data_range[2], max_row=data_range[3])
        categories = Reference(ws,
                              min_col=categories_range[0], min_row=categories_range[1],
                              max_col=categories_range[2], max_row=categories_range[3])
        
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categories)
        
        # Set size
        chart.width = 15
        chart.height = 10
        
        return chart
    
    @staticmethod
    def create_velocity_chart(
        ws: Worksheet,
        start_row: int,
        sprint_col: int,
        committed_col: int,
        completed_col: int,
        num_sprints: int
    ) -> BarChart:
        """
        Create a velocity chart comparing committed vs completed points.
        
        Args:
            ws: Worksheet containing velocity data
            start_row: First data row (after header)
            sprint_col: Column with sprint names
            committed_col: Column with committed points
            completed_col: Column with completed points
            num_sprints: Number of sprints to display
            
        Returns:
            Configured BarChart for velocity
        """
        chart = BarChart()
        chart.type = "col"
        chart.style = 26
        chart.title = "Sprint Velocity"
        chart.y_axis.title = "Story Points"
        chart.x_axis.title = "Sprint"
        
        # Data: committed and completed
        data = Reference(ws,
                        min_col=committed_col,
                        min_row=start_row - 1,  # Include header
                        max_col=completed_col,
                        max_row=start_row + num_sprints - 1)
        
        # Categories: sprint names
        cats = Reference(ws,
                        min_col=sprint_col,
                        min_row=start_row,
                        max_row=start_row + num_sprints - 1)
        
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)
        
        chart.width = 15
        chart.height = 10
        
        return chart
    
    @staticmethod
    def create_burndown_chart(
        ws: Worksheet,
        start_row: int,
        date_col: int,
        remaining_col: int,
        ideal_col: int,
        num_days: int
    ) -> LineChart:
        """
        Create a sprint burndown chart.
        
        Args:
            ws: Worksheet containing burndown data
            start_row: First data row (after header)
            date_col: Column with dates
            remaining_col: Column with remaining work
            ideal_col: Column with ideal burndown line
            num_days: Number of days in sprint
            
        Returns:
            Configured LineChart for burndown
        """
        chart = LineChart()
        chart.style = 26
        chart.title = "Sprint Burndown"
        chart.y_axis.title = "Remaining Points"
        chart.x_axis.title = "Day"
        
        # Data: remaining and ideal
        data = Reference(ws,
                        min_col=remaining_col,
                        min_row=start_row - 1,
                        max_col=ideal_col,
                        max_row=start_row + num_days - 1)
        
        # Categories: dates
        cats = Reference(ws,
                        min_col=date_col,
                        min_row=start_row,
                        max_row=start_row + num_days - 1)
        
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)
        
        # Make ideal line dashed
        if len(chart.series) > 1:
            chart.series[1].graphicalProperties.line.dashStyle = "dash"
        
        chart.width = 15
        chart.height = 10
        
        return chart
    
    @staticmethod
    def create_status_distribution_chart(
        ws: Worksheet,
        start_row: int,
        status_col: int,
        count_col: int,
        num_statuses: int
    ) -> PieChart:
        """
        Create a pie chart showing issue status distribution.
        
        Args:
            ws: Worksheet containing status data
            start_row: First data row (after header)
            status_col: Column with status names
            count_col: Column with counts
            num_statuses: Number of status types
            
        Returns:
            Configured PieChart for status distribution
        """
        chart = PieChart()
        chart.style = 11
        chart.title = "Status Distribution"
        
        data = Reference(ws,
                        min_col=count_col,
                        min_row=start_row - 1,
                        max_row=start_row + num_statuses - 1)
        
        cats = Reference(ws,
                        min_col=status_col,
                        min_row=start_row,
                        max_row=start_row + num_statuses - 1)
        
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)
        
        # Show percentages
        chart.dataLabels = DataLabelList()
        chart.dataLabels.showPercent = True
        chart.dataLabels.showCatName = True
        
        chart.width = 12
        chart.height = 10
        
        return chart
