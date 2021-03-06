source('lib.R')

doAnchor = function(fpath, save=F) {
    data = read.csv(fpath, header=T)
    maxTime = max(data$time)
    
    # Smaller plot margins
    b = 2.5; t = 2
    l = b; r = t
    par(mar=c(b, l, t, r))
    
    windowWidths = c(toString(maxTime), '9<t<91')
    dataSets = list(data
                    , subset(data, subset= (time > 9) & (time < 91)))
    for (ix in 1:length(dataSets)) {
        x = dataSets[[ix]]
        window = windowWidths[[ix]]
        gByIX = split(x, x$ix)  # over >1 time value
        # collapse times into one statistic
        # v_min1qMedianMean3qMax = summary(gByIX[[1]]$value)
        statsPerIx = mapply(gByIX, FUN = function(df) summary(df$value))
        
        # Set up saving if chosen
        imgPath = NULL
        if (save) {
            imgPath = 'anchor forces boxplot angle=%i window=%s.png'
            imgPath = sprintf(imgPath, angle, window)
        }
        saveFunc = getSaveFunc(imgPath)
        
        boxplot(statsPerIx)  # <-- What I want
        title(sprintf('angle=%.0f window=%s', angle, window))
        saveFunc()
    }
}

anchorAngles = c(15)
anchorPathTemplate = 
    '../dumps/hw=1.5d grain_h=20 g=2.0 damp=-10 dt=0.01/angle=%i/10001/anchor_accels.csv'
cat('Starting anchor force analysis\n')
for (angle in anchorAngles) {
    fpath = sprintf(anchorPathTemplate, angle)
    cat("angle =", angle, '\n')
    doAnchor(fpath, save=F)
}

stop("quit early")
# fpath = '../dumps/hw=0.0d grain_h=30 g=2.0 damp=-10 dt=0.01/angle=15/anchor_accels_funky_ixs.csv'


data = read.csv(fpath, header=T)
x = data
maxTime = max(x$time)
# x$ix = factor(x$ix)  # stringifies, FYI
# x$time = factor(x$time)
# Oddly large values, and for the middle anchors generally
x$time[x$value > 100]
x$ix[x$value > 100]

# numToTake = length(unique(x$ix)) * 10
# # steady = subset(x, subset= time > 15)  # arbitrary
# steady = tail(x, n=numToTake)
# 
# x = steady
# gs = split(x, x$ix)  # creates a list of dfs with keys=ixs (as strings e.g. "0")
# summary(gs[[1]]$value)
# sd(gs[[1]]$value)

# Smaller plot margins
b = 2.5; t = 1
l = b; r = t
par(mar=c(b, l, t, r))

for (x in list(data, subset(data, subset= time > maxTime-1))) {
    gByIX = split(x, x$ix)  # over >1 time value
    # collapse times into one statistic
    # v_min1qMedianMean3qMax = summary(gByIX[[1]]$value)
    statsPerIx = mapply(gByIX, FUN = function(df) summary(df$value))
    boxplot(statsPerIx)  # <-- What I want
    # rows are stat headings, so transpose to get those as col names and ix's as rows
    df = as.data.frame(t(statsPerIx))
}


# barplot(x$value[x$time == x$time[[10]]])
# Maybe color those left of the middle differently
