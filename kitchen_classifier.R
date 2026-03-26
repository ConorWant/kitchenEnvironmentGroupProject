library(randomForest)
library(jsonlite)

args <- commandArgs(trailingOnly = TRUE)
input_csv  <- if (length(args) >= 1) args[1] else "sensor_log.csv"
output_json <- if (length(args) >= 2) args[2] else "status.json"

set.seed(42)

df <- read.csv(input_csv)
df$unsafe <- factor(
  as.integer((df$temperature_c > 8.0) | (df$light_lux > 200.0)),
  levels = c(0, 1), labels = c("Safe", "Unsafe")
)

train_idx  <- sample(1:nrow(df), size = 0.8 * nrow(df))
rf_model   <- randomForest(unsafe ~ temperature_c + light_lux,
                            data = df[train_idx, ], ntree = 100)

# Classify ALL rows
df$status <- as.character(predict(rf_model, newdata = df))

result <- df[, c("timestamp", "fridge_type", "fridge_number", "status")]
write_json(result, path = output_json, auto_unbox = TRUE)
cat(sprintf("Classified %d readings -> %s\n", nrow(df), output_json))
