from plotly import tools
import plotly as py
import plotly.graph_objs as go
print("starting to plot")  # add multiple trace support with tags for more interesting data
file = open('data.txt')   # remove any values outside 1 std dev from mean
upper_x = []
upper_y = []
upper_z = []
lower_x = []
lower_y = []
lower_z = []
sets = [upper_x, upper_y, upper_z, lower_x, lower_y, lower_z]
for line in file:
    line = line.strip('\n')
    data = line.split(' ')
    if len(data) is 7:
        for i in range(len(data)-1):
            sets[i].append(float(data[i]))
    else:
        print(data)
temp = range(0, len(upper_x) * 20, 20)  # creates a decimal time range for the x-axis (maybe replace with real times?)
x_axis = []  # this looks stupid, but it makes plotly not screw up
for num in temp:
    x_axis.append(num / 100)
# maybe figure out how to differentiate positions to clarify the graphs- a time stamp would do this
print(sets)
print(x_axis)
trace1 = go.Scatter(
    x=x_axis,
    y=upper_x
)
trace2 = go.Scatter(
    x=x_axis,
    y=upper_y
)
trace3 = go.Scatter(
    x=x_axis,
    y=upper_z
)
trace4 = go.Scatter(
    x=x_axis,
    y=lower_x
)
trace5 = go.Scatter(
    x=x_axis,
    y=lower_y
)
trace6 = go.Scatter(
    x=x_axis,
    y=lower_z
)

fig = tools.make_subplots(rows=2, cols=3,
                          subplot_titles=('Upper Yaw', 'Upper Pitch', 'Upper Roll', 'Lower Yaw', 'Lower Pitch', 'Lower Roll'))

fig.append_trace(trace1, 1, 1)
fig.append_trace(trace2, 1, 2)
fig.append_trace(trace3, 1, 3)
fig.append_trace(trace4, 2, 3)
fig.append_trace(trace5, 2, 2)
fig.append_trace(trace6, 2, 1)

fig['layout'].update(height=600, width=600, title='Gyroscope Readings')
plot_url = py.offline.plot(fig, filename='make-subplots.html')
