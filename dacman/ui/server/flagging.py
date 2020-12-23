import math
import pandas as pd

def frontend_format(data):
    data_dict = data.to_dict(orient='split')

    print(data_dict)
    #return {'hello': 'hello'}

    cols = [{'field': 'id', 'headerName': 'ID'}]
    datasetVars = []
    for i, col in enumerate(data_dict['columns']):
        cols.append({'field': col})
        datasetVars.append({
            'varName': col,
            'contentType': 'string' if str(data.dtypes[i]) == 'object' else str(data.dtypes[i])
        })

    rows = []
    for i, row in enumerate(data_dict['data'], start=1):
        clean_row = {'id': i}
        for j, element in enumerate(row):
            if isinstance(element, float) and math.isnan(element):
                clean_row[cols[j]['field']] = str(element)
            else:
                clean_row[cols[j]['field']] = element
        rows.append(clean_row)
    

    formatted_data = {
        'columns': cols,
        'rows': rows,
        'datasetVars': datasetVars
    }

    return formatted_data

def read_csv(file_path):
    data = pd.read_csv(file_path)
    formatted_data = frontend_format(data.head(10))

    return formatted_data
