import streamlit as st

def layout_three_areas(left_ratio=1, center_ratio=2.5, right_ratio=1, gap="medium"):
    """
    Creates three main areas: left (modules/filesystem), center (action area), right (chat)
    
    Args:
        left_ratio (float): Width ratio for left area
        center_ratio (float): Width ratio for center area  
        right_ratio (float): Width ratio for right area
        gap (str): Gap between columns ("small", "medium", "large")
    
    Returns:
        tuple: (left_area, center_area, right_area)
    """
    left_area, center_area, right_area = st.columns([left_ratio, center_ratio, right_ratio], gap=gap)
    return left_area, center_area, right_area

def layout_left_area(width_ratio=1, position="left"):
    """
    Creates the left area for modules and file system
    
    Args:
        width_ratio (float): Width of the left area
        position (str): Position of the area
    
    Returns:
        streamlit.container: Left area container
    """
    if position == "left":
        left_col, _ = st.columns([width_ratio, 10-width_ratio])
        return left_col
    else:
        return st.container()

def layout_center_area(width_ratio=2.5, position="center", offset_left=1, offset_right=1):
    """
    Creates the center area for main actions and analysis
    
    Args:
        width_ratio (float): Width of the center area
        position (str): Position of the area
        offset_left (float): Space from left edge
        offset_right (float): Space from right edge
    
    Returns:
        streamlit.container: Center area container
    """
    if position == "center":
        _, center_col, _ = st.columns([offset_left, width_ratio, offset_right])
        return center_col
    else:
        return st.container()

def layout_right_area(width_ratio=1, position="right"):
    """
    Creates the right area for chat interface
    
    Args:
        width_ratio (float): Width of the right area
        position (str): Position of the area
    
    Returns:
        streamlit.container: Right area container
    """
    if position == "right":
        _, right_col = st.columns([10-width_ratio, width_ratio])
        return right_col
    else:
        return st.container()

def layout_custom_grid(layout_config):
    """
    Creates a custom grid layout based on configuration
    
    Args:
        layout_config (dict): Configuration for layout
            Example: {
                'areas': ['left', 'center', 'right'],
                'ratios': [1, 2.5, 1],
                'gap': 'medium',
                'heights': ['auto', 'auto', 'auto']  # Future feature
            }
    
    Returns:
        dict: Dictionary with area names as keys and containers as values
    """
    areas = layout_config.get('areas', ['left', 'center', 'right'])
    ratios = layout_config.get('ratios', [1, 2.5, 1])
    gap = layout_config.get('gap', 'medium')
    
    if len(areas) != len(ratios):
        raise ValueError("Number of areas must match number of ratios")
    
    columns = st.columns(ratios, gap=gap)
    
    result = {}
    for i, area_name in enumerate(areas):
        result[area_name] = columns[i]
    
    return result

def layout_flexible_areas(config_dict):
    """
    Most flexible layout function - allows complete customization
    
    Args:
        config_dict (dict): Complete layout configuration
            Example: {
                'layout_type': 'three_column',  # 'three_column', 'two_column', 'single'
                'left': {'ratio': 1, 'visible': True},
                'center': {'ratio': 2.5, 'visible': True},
                'right': {'ratio': 1, 'visible': True},
                'gap': 'medium',
                'borders': {'left': False, 'center': False, 'right': False}
            }
    
    Returns:
        dict: Dictionary with configured areas
    """
    layout_type = config_dict.get('layout_type', 'three_column')
    gap = config_dict.get('gap', 'medium')
    
    areas = {}
    
    if layout_type == 'three_column':
        left_config = config_dict.get('left', {'ratio': 1, 'visible': True})
        center_config = config_dict.get('center', {'ratio': 2.5, 'visible': True})
        right_config = config_dict.get('right', {'ratio': 1, 'visible': True})
        
        visible_ratios = []
        visible_areas = []
        
        if left_config['visible']:
            visible_ratios.append(left_config['ratio'])
            visible_areas.append('left')
        if center_config['visible']:
            visible_ratios.append(center_config['ratio'])
            visible_areas.append('center')
        if right_config['visible']:
            visible_ratios.append(right_config['ratio'])
            visible_areas.append('right')
        
        if visible_ratios:
            columns = st.columns(visible_ratios, gap=gap)
            for i, area_name in enumerate(visible_areas):
                areas[area_name] = columns[i]
    
    elif layout_type == 'two_column':
        col1, col2 = st.columns([2, 1], gap=gap)
        areas['main'] = col1
        areas['side'] = col2
    
    elif layout_type == 'single':
        areas['main'] = st.container()
    
    return areas

def layout_get_coordinates(area_name, config):
    """
    Simulates coordinate system for area positioning
    (Note: Streamlit doesn't support absolute positioning, this is for reference)
    
    Args:
        area_name (str): Name of the area
        config (dict): Layout configuration
    
    Returns:
        dict: Simulated coordinates and dimensions
    """
    coordinates = {
        'left': {'x': 0, 'y': 0, 'width': config.get('left_width', 1), 'height': '100vh'},
        'center': {'x': config.get('left_width', 1), 'y': 0, 'width': config.get('center_width', 2.5), 'height': '100vh'},
        'right': {'x': config.get('left_width', 1) + config.get('center_width', 2.5), 'y': 0, 'width': config.get('right_width', 1), 'height': '100vh'}
    }
    
    return coordinates.get(area_name, {'x': 0, 'y': 0, 'width': 1, 'height': '100vh'})
