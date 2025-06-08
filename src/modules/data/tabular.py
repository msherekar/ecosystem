import streamlit as st
import pandas as pd
import numpy as np
from src.chat.chatbot import ask_chatbot
import plotly.express as px

# Remove conflicting session state initialization - this is handled by session.py
# The existing session state variables will be used from the main app

st.markdown("""
    <style>
    .border-box {
        border: 2px solid #2196F3;
        padding: 20px;
        border-radius: 8px;
        background-color: #eef7ff;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

def control_panel():
    
    edit_cols = st.columns([0.9,0.9,0.7,0.8,0.9,1,1,1.1,0.8, 0.8])  # All columns have the same small width
    labels = ["Create", "Insights", "Sort", "Filter", "Insert", "Formula", "Group", "Summary", "Merge", "Reset"]

    for col, label in zip(edit_cols, labels):
        with col:
            if col.button(label, key = f'key_{label}', use_container_width=True):
                st.session_state.clicked_button = label

    plot_cols = st.columns([0.8,0.8,0.8,0.8])
    labels = ["Plots", "XY", "Column", "Heatmap"]
    for col, label in zip(plot_cols, labels):
        with col:
            if col.button(label, key = f'key_{label}', use_container_width=True):
                st.session_state.clicked_button = label

if st.session_state.get("clicked_button") == "Reset":
    st.session_state.clicked_button = None

def tool_insights(df):
    
    summary = {
    "shape": df.shape,
    "columns": list(df.columns),
    "dtypes": df.dtypes.astype(str).to_dict(),
    "null_counts": df.isnull().sum().to_dict(),
    "preview": df.head(5).to_dict(orient="records"),
    "description": df.describe(include="all").to_dict()
}
    prompt = f"""
                You are a data analysis assistant. A user uploaded a dataset in tabular format. Below is a summary of the dataset:

                - Shape: {summary['shape']}
                - Columns: {summary['columns']}
                - Data types: {summary['dtypes']}
                - Null value counts: {summary['null_counts']}
                - First 5 rows of data:
                {summary['preview']}

                Your tasks:
                1. Try to **identify what kind of dataset this is** (e.g., DESeq2 results, sales data, medical records, etc.).
                2. Give **key insights** from the data (e.g., how many entries are statistically significant).
                4. Suggest next steps the user might take (e.g., filtering, plotting).
                Respond in a clear and concisely.
                """
    message = ask_chatbot(user_question=[{"role": "user", "content": prompt}], model_choice='gpt4')
    return message.content

def tool_sort(df):
    mod_df = df.copy()
    with st.expander("Select the column to sort by"):
                    option = st.selectbox("", placeholder= "Column name", index = None, options= df.columns, key=f"sort_option")
                    if option:
                        mod_df = df.sort_values(by=option)
    return mod_df

def tool_filter(df):
    mod_df = df.copy()
    with st.expander("Filter Options"):
        option = st.selectbox("Select column to filter by", df.columns, key=f"filter_option")
        if option:
            col_dtype = df[option].dtype
            if np.issubdtype(col_dtype, np.number):
                min_value = st.number_input("Min value", value=float(df[option].min()), key=f"min_value")
                max_value = st.number_input("Max value", value=float(df[option].max()), key=f"max_value")
                mod_df = df[(df[option] > min_value) & (df[option] < max_value)]
            elif pd.api.types.is_string_dtype(col_dtype):
                search_str = st.text_input("Enter a string to search", key=f"search_str")
                mod_df = df[df[option].str.contains(search_str, na=False)]
            elif pd.api.types.is_bool_dtype(col_dtype):
                bool_value = st.checkbox("Filter for True values", key=f"bool_value")
                mod_df = df[df[option] == bool_value]
    return mod_df

def tool_insert(df):
    mod_df = df.copy()
    with st.expander("Insert a new column"):
        new_col_name = st.text_input("New column name", key = f"new_col_name")
        new_col_index = int(st.number_input("Index of the new column", key = f"new_col_index"))
        new_col_type = st.selectbox(f"Data type for column", ["str", "int", "float", "bool"], key=f"coln_type")
        if st.button("Add Column"):
            if new_col_name in mod_df.columns:
                st.warning("Column name already exists.")
            else:
                default_values = {"str": "", "int": 0, "float": 0.0, "bool": False}
                default_value = default_values[new_col_type]
                new_series = pd.Series([default_value] * len(mod_df), index=mod_df.index)
                mod_df.insert(new_col_index, new_col_name, new_series)
                    
                st.success(f"Column '{new_col_name}' added.")
    return mod_df

def tool_formula(df):
    mod_df = df.copy()
    with st.expander("Add a Formula using column names"):
        new_col_name = st.text_input("New column name", key = f"new_col_name")
        formula = st.text_input("Enter a formula using existing columns", help="E.g., col1 + col2 * 2")
        if st.button("Add Column"):
            if new_col_name in df.columns:
                st.warning("Column name already exists.")
            elif not new_col_name or not formula:
                st.warning("Please provide both a name and formula.")
            else:
                try:
                    mod_df[new_col_name] = df.eval(formula, engine='python')
                    st.success(f"Column '{new_col_name}' added.")
                except Exception as e:
                    st.error(f"Error in formula: {e}")

    return mod_df

def process_uploaded_file(file):
    try:
        if file.endswith(".csv"):
            # Smart delimiter detection for CSV files
            with open(file, 'r', encoding='utf-8') as f:
                sample = f.read(1024)
                f.seek(0)
                # Determine delimiter by counting tabs vs commas in the sample
                delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
                return pd.read_csv(file, sep=delimiter)
        elif file.endswith(".xlsx"):
            return pd.read_excel(file)
        elif file.endswith(".txt"):
            # For .txt files, also do smart delimiter detection
            with open(file, 'r', encoding='utf-8') as f:
                sample = f.read(1024)
                f.seek(0)
                delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
                return pd.read_csv(file, sep=delimiter)
        else:
            st.error("Unsupported file format.")
            return None
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

def tool_group(df):
    mod_df = df.copy()
    
    with st.expander("Select the columns to group"):
        option = st.multiselect(
            label="Group by columns", 
            placeholder="Column name", 
            options=df.columns, 
            key="group_option"
        )
        if option:
            # Display aggregation method
            agg_method = st.selectbox("Aggregation method", ["mean", "sum", "count"], key="agg_method")

            # Perform aggregation
            
            if agg_method == "count":
                mod_df = df.groupby(option).count().reset_index()
            elif agg_method == "mean":
                mod_df = df.groupby(option).mean(numeric_only=True).reset_index()
            elif agg_method == "sum":
                mod_df = df.groupby(option).sum(numeric_only=True).reset_index()

    return mod_df

def tool_merge(modified_dfs):
    if not modified_dfs or len(modified_dfs) < 2:
        st.info("At least two dataframes are required to perform a merge.")
        return None
    
    options = list(st.session_state.modified_df.keys())
    with st.expander("Select dataframes to merge"):
        # Create a unique key for this multiselect based on the current dataframe
        current_df_key = list(modified_dfs.keys())[0] if modified_dfs else "default"
        selected_dfs = st.multiselect(
            label="Select two dataframes to merge",
            options=options,
            max_selections=2,
            key=f"merge_df_selector_{current_df_key}"
        )

        if len(selected_dfs) == 2:
            df1, df2 = modified_dfs[selected_dfs[0]], modified_dfs[selected_dfs[1]]

            # Find common columns
            common_cols = list(set(df1.columns) & set(df2.columns))

            if not common_cols:
                st.warning("No common columns found to merge on. Cannot perform merge.")
                return None

            merge_col = st.selectbox(
                label="Select column to merge on",
                options=common_cols,
                key=f"merge_col_selector_{current_df_key}"
            )

            merge_type = st.selectbox(
                label="Select merge type",
                options=["inner", "left", "right", "outer"],
                key=f"merge_type_selector_{current_df_key}"
            )

            if st.button("Merge", key=f"merge_button_{current_df_key}"):
                try:
                    merged_df = pd.merge(df1, df2, on=merge_col, how=merge_type)
                    st.success("Merge successful!")
                    return merged_df
                except Exception as e:
                    st.error(f"Merge failed: {e}")

        return None

def create(new_file_name):
    df = None
    if new_file_name:
        with st.form("add_multiple_columns"):
            num_cols = st.number_input("How many columns to add?", min_value=1, max_value=10, step=1, key="num_cols")
            default_rows = st.number_input("Default number of rows", value=5, min_value=1, key="default_rows")

            col_names = []
            col_types = []

            for i in range(num_cols):
                st.markdown(f"**Column {i+1}**")
                col_name = st.text_input(f"Name for column {i+1}", key=f"col_name_{i}")
                col_type = st.selectbox(
                    f"Data type for column {i+1}", ["str", "int", "float", "bool"], key=f"col_type_{i}"
                )
                col_names.append(col_name)
                col_types.append(col_type)

            submitted = st.form_submit_button("Create table")

            if submitted:
                if all(name for name in col_names):
                    if len(set(col_names)) < len(col_names):
                        st.warning("Column names must be unique.")
                    else:
                        default_values = {"str": "", "int": 0, "float": 0.0, "bool": False}
                        df = pd.DataFrame()
                        for name, dtype in zip(col_names, col_types):
                            df[name] = pd.Series([default_values[dtype]] * default_rows, dtype=dtype)
                         # Clean up form state
                        for i in range(num_cols):
                            st.session_state.pop(f"col_name_{i}", None)
                            st.session_state.pop(f"col_type_{i}", None)
                        st.session_state.pop("num_cols", None)
                        st.session_state.pop("default_rows", None)

                        # Refresh UI
                        st.success(f"Table '{new_file_name}' created.")

                else:
                    st.warning("Please fill in all column names.")
                
    return df

def display_dataframe(dataframe_dict):
    for key, df in dataframe_dict.items():
        if df is not None:
            st.markdown(f"Viewing **{key}**, **{df.shape[0]}** rows, **{df.shape[1]}** columns")
            st.dataframe(df, use_container_width=True)

def display_file_summary(df, filename):
    """Display a comprehensive summary of the uploaded file"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Rows", df.shape[0])
    with col2:
        st.metric("Columns", df.shape[1])
    with col3:
        st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
    
    # Show column types summary
    dtype_counts = df.dtypes.value_counts()
    st.write("**Column Types:**")
    for dtype, count in dtype_counts.items():
        st.write(f"- {dtype}: {count} columns")
    
    # For files with many columns, show a scrollable column list
    if len(df.columns) > 10:
        with st.expander(f"View all {len(df.columns)} columns"):
            cols_per_row = 4
            for i in range(0, len(df.columns), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    if i + j < len(df.columns):
                        col_name = df.columns[i + j]
                        col_type = str(df[col_name].dtype)
                        with col:
                            st.write(f"**{col_name}**")
                            st.write(f"Type: {col_type}")
    else:
        st.write("**Columns:**")
        for col in df.columns:
            st.write(f"- {col} ({df[col].dtype})")

def editing_dataframe(dataframe_dict):
    # Handle merge operation separately if it's selected
    if st.session_state.get("clicked_button") == "Merge":
        merged_df = tool_merge(st.session_state.modified_df)
        if merged_df is not None:
            st.session_state.modified_df["Merged_Data"] = merged_df
            st.session_state.original_df["Merged_Data"] = merged_df
            st.success("Merged file added as 'Merged_Data'")
        return

    # Handle other operations for each dataframe
    for key in dataframe_dict:
        df = dataframe_dict[key].copy()
        if df is not None:
            mod_df = df # make a copy of the data before doing an operation
            if st.session_state.get("clicked_button") == "Sort":
                mod_df = tool_sort(mod_df)
            if st.session_state.get("clicked_button") == "Filter":
                mod_df = tool_filter(mod_df)            
            if st.session_state.get("clicked_button") == "Insert":
                mod_df = tool_insert(mod_df)
            if st.session_state.get("clicked_button") == "Formula":
                mod_df = tool_formula(mod_df)
                st.session_state.modified_df[key] = mod_df
            if st.session_state.get("clicked_button") == "Group":
                mod_df = tool_group(mod_df)
            
            edited_df = st.data_editor(
                mod_df, 
                num_rows="dynamic", 
                key=f"data_editor_{key}", 
                use_container_width=True,
                column_config={
                    col: st.column_config.Column(
                        width="medium" if len(mod_df.columns) > 10 else "large"
                    ) for col in mod_df.columns
                }
            )

            st.write(edited_df.shape)
            button1, button2 = st.columns(2)
            if button1.button(f"Save file", key=f"save_button_{key}", use_container_width=True):
                if not edited_df.equals(df):
                    st.session_state.modified_df[key] = edited_df
                    st.success("File saved successfully.")
                    st.session_state.clicked_button = None
                else:
                    st.info("No changes to save.")
            if button2.button(f"Cancel changes", key=f'cancel_button_{key}', use_container_width=True):
                st.session_state.modified_df[key] = st.session_state.original_df[key]
                st.rerun()

def plot_XY(df_dict):
    with st.expander("Select columns to plot"):
            key = st.selectbox("Select the dataframe", options = df_dict.keys(), key="df_selector")
            df = df_dict[key]
            # Get numeric columns from the DataFrame
            numeric_cols = df.select_dtypes(include='number').columns.tolist()
            
            if not numeric_cols:
                st.warning("No numeric columns found in the dataset.")
                return None
            else:
                X_col = st.selectbox("Select X-axis column", placeholder="Enter X", options=numeric_cols, key="X_selector")
                Y_col = st.selectbox("Select Y-axis column", placeholder = "Enter Y", options=numeric_cols, key="Y_selector")
                if st.button("Plot", key = "plot"):
                    if X_col and Y_col:
                        fig = px.scatter(df, x=X_col, y=Y_col)
                        # Update font colors to black and add black axis lines with increased font sizes
                        fig.update_layout(
                            xaxis_title_font_color='black',
                            xaxis_title_font_size=20,  # Increased x-axis title font size
                            yaxis_title_font_color='black',
                            yaxis_title_font_size=20,  # Increased y-axis title font size
                            xaxis=dict(
                                tickfont=dict(color='black', size=16),  # Increased tick label font size
                                linecolor='black',
                                showline=True,
                                linewidth=1,
                                mirror=True
                            ),
                            yaxis=dict(
                                tickfont=dict(color='black', size=16),  # Increased tick label font size
                                linecolor='black',
                                showline=True,
                                linewidth=1,
                                mirror=True
                            ),
                            plot_bgcolor='white',
                            paper_bgcolor='white',
                            showlegend=False,
                            margin=dict(l=60, r=30, t=30, b=60)
                        )
                        return fig
    return None

def plot_column(df_dict):
    with st.expander("Select columns to plot"):
            key = st.selectbox("Select the dataframe", options = df_dict.keys(), key="col_df_selector")
            df = df_dict[key]
            
            # Get categorical and numerical columns
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            if not cat_cols or not num_cols:
                st.warning("Need both categorical and numerical columns for plotting.")
                return None
            else:
                cat_col = st.selectbox("Select categorical column", options=cat_cols, key="cat_col_selector")
                num_col = st.selectbox("Select numerical column", options=num_cols, key="num_col_selector")
                if st.button("Plot", key = "col_plot"):
                    if cat_col and num_col:
                        # Create bar plot with categorical x-axis and numerical y-axis
                        fig = px.bar(df, x=cat_col, y=num_col)
                        
                        # Update layout with consistent styling
                        fig.update_layout(
                            xaxis_title_font_color='black',
                            xaxis_title_font_size=20,
                            yaxis_title_font_color='black',
                            yaxis_title_font_size=20,
                            xaxis=dict(
                                tickfont=dict(color='black', size=16),
                                linecolor='black',
                                showline=True,
                                linewidth=1,
                                mirror=True
                            ),
                            yaxis=dict(
                                tickfont=dict(color='black', size=16),
                                linecolor='black',
                                showline=True,
                                linewidth=1,
                                mirror=True
                            ),
                            plot_bgcolor='white',
                            paper_bgcolor='white',
                            showlegend=False,
                            margin=dict(l=60, r=30, t=30, b=60)
                        )
                        return fig
    return None

def plot_heatmap(df_dict):
    with st.expander("Select columns to plot"):
        key = st.selectbox("Select the dataframe", options=df_dict.keys(), key="heatmap_df_selector")
        df = df_dict[key]

        # Get categorical and numerical columns
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        num_cols = df.select_dtypes(include=['number']).columns.tolist()

        if not cat_cols or not num_cols:
            st.warning("Need both categorical and numerical columns for plotting.")
        else:
            cat_col = st.selectbox("Select categorical column (for rows)", options=cat_cols, key="cat_col_selector")
            num_col = st.multiselect("Select numerical columns (for heatmap)", options=num_cols, key="num_col_selector")

            if st.button("Plot Heatmap", key="heatmap_plot"):
                if cat_col and num_col:
                    try:
                        heatmap_data = df[[cat_col] + num_col].dropna()
                        heatmap_data.set_index(cat_col, inplace=True)

                        fig = px.imshow(
                            heatmap_data.values,
                            labels=dict(y=cat_col, color="Value"),
                            x=num_col,
                            y=heatmap_data.index.astype(str),
                            text_auto=True,
                            aspect="auto"
                        )
                        
                        # Update layout with consistent styling
                        fig.update_layout(
                            xaxis_title_font_color='black',
                            xaxis_title_font_size=20,
                            yaxis_title_font_color='black',
                            yaxis_title_font_size=20,
                            xaxis=dict(
                                tickfont=dict(color='black', size=16),
                                linecolor='black',
                                showline=True,
                                linewidth=1,
                                mirror=True,
                                title=None  # Remove x-axis title
                            ),
                            yaxis=dict(
                                tickfont=dict(color='black', size=16),
                                linecolor='black',
                                showline=True,
                                linewidth=1,
                                mirror=True
                            ),
                            plot_bgcolor='white',
                            paper_bgcolor='white',
                            showlegend=False,
                            margin=dict(l=60, r=30, t=30, b=60)
                        )
                        
                        # Update colorbar styling
                        fig.update_coloraxes(
                            colorbar=dict(
                                tickfont=dict(color='black', size=16),
                                title_font=dict(color='black', size=20)
                            )
                        )
                        
                        return fig
                    except Exception as e:
                        return st.error(f"Error creating heatmap: {e}")
                else:
                    return st.warning("Please select both a categorical and at least one numerical column.")


def tabular_data():
    """Main function to render the complete tabular analysis interface"""
    # Initialize tabular-specific session state if not exists
    if "clicked_button" not in st.session_state:
        st.session_state.clicked_button = None
    if "is_plot" not in st.session_state:
        st.session_state.is_plot = False
    if "figures" not in st.session_state:
        st.session_state.figures = []
    
    # Show header only if there are uploaded files
    if st.session_state.get("original_df") and st.session_state.original_df:
        st.markdown("### Tabular Data Analysis")
    else:
        st.markdown("### Tabular Data Analysis")
        st.info("Upload tabular data files from the left panel to begin analysis.")
        return
    
    control_panel()
    
    if st.session_state.get("clicked_button") == "Create":
        with st.expander("Click here to create a new file"):
            new_file_name = st.text_input("Create a file")
            new_df = create(new_file_name)
            if new_df is not None and new_file_name not in st.session_state.modified_df:
                st.session_state.modified_df[new_file_name] = new_df
                st.session_state.original_df[new_file_name] = new_df
                st.session_state.clicked_button = None
                st.rerun()
    
    if st.session_state.get("clicked_button") == "XY":
        if st.session_state.modified_df:
            fig = plot_XY(st.session_state.modified_df)
            if fig:
                st.session_state.figures.append(fig)
                st.session_state.is_plot = True
        else:
            st.warning("No data available for plotting.")
    
    if st.session_state.get("clicked_button") == "Column":
        if st.session_state.modified_df:
            fig = plot_column(st.session_state.modified_df)
            if fig:
                st.session_state.figures.append(fig)
                st.session_state.is_plot = True
        else:
            st.warning("No data available for plotting.")
    
    if st.session_state.get("clicked_button") == "Heatmap":
        if st.session_state.modified_df:
            fig = plot_heatmap(st.session_state.modified_df)
            if fig:
                st.session_state.figures.append(fig)
                st.session_state.is_plot = True
        else:
            st.warning("No data available for plotting.")
    
    # Display all figures
    if st.session_state.get("figures") and st.session_state.get("is_plot"):
        for i, fig in enumerate(st.session_state.figures):
            st.plotly_chart(fig, use_container_width=True, key=f"plot_{i}")
            if st.button(f"Remove Plot {i+1}", key=f"remove_plot_{i}"):
                st.session_state.figures.pop(i)
                st.rerun()
    
    # Show the editable/newest file on top
    if st.session_state.get("clicked_button") == "Insights":
        if st.session_state.modified_df:
            df = list(st.session_state.modified_df.values())[-1]
            message = tool_insights(df)
            # Ensure messages list exists
            if "messages" not in st.session_state:
                st.session_state.messages = []
            st.session_state.messages.append({"role": "assistant", "content": message})
        st.session_state.clicked_button = None

    # Main data editing interface
    if st.session_state.get("modified_df") and st.session_state.modified_df:
        # Show file summaries first
        st.markdown("**Uploaded Files Summary:**")
        for filename, df in st.session_state.modified_df.items():
            with st.expander(f"File: {filename} ({df.shape[0]} rows × {df.shape[1]} columns)", expanded=False):
                display_file_summary(df, filename)
        
        with st.container():
            st.markdown("---")
            editing_dataframe(st.session_state.modified_df)
            st.markdown("---")
