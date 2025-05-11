# Regla para lanzar el scraper de futuros todos los días a las 23:00 UTC
resource "aws_cloudwatch_event_rule" "futuros_scraper_daily" {
  name                = "futuros-scraper-daily"
  schedule_expression = "cron(0 23 * * ? *)"
  description         = "Lanza la Lambda de scraping de futuros todos los días a las 23:00 UTC"
}

resource "aws_cloudwatch_event_target" "futuros_scraper_target" {
  rule      = aws_cloudwatch_event_rule.futuros_scraper_daily.name
  target_id = "scraperFuturosLambda"
  arn       = aws_lambda_function.scraper_futuros.arn
}

resource "aws_lambda_permission" "allow_eventbridge_futuros" {
  statement_id  = "AllowExecutionFromEventBridgeFuturos"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scraper_futuros.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.futuros_scraper_daily.arn
}

# Regla para lanzar el scraper de opciones todos los días a las 23:00 UTC
resource "aws_cloudwatch_event_rule" "opciones_scraper_daily" {
  name                = "opciones-scraper-daily"
  schedule_expression = "cron(0 23 * * ? *)"
  description         = "Lanza la Lambda de scraping de opciones todos los días a las 23:00 UTC"
}

resource "aws_cloudwatch_event_target" "opciones_scraper_target" {
  rule      = aws_cloudwatch_event_rule.opciones_scraper_daily.name
  target_id = "scraperV2Lambda"
  arn       = aws_lambda_function.scraper_v2.arn
}

resource "aws_lambda_permission" "allow_eventbridge_opciones" {
  statement_id  = "AllowExecutionFromEventBridgeOpciones"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scraper_v2.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.opciones_scraper_daily.arn
}

# Regla para lanzar el cálculo de IV todos los días a las 23:20 UTC
resource "aws_cloudwatch_event_rule" "iv_calculation_daily" {
  name                = "iv-calculation-daily"
  schedule_expression = "cron(20 23 * * ? *)"
  description         = "Lanza la Lambda de cálculo de IV todos los días a las 23:20 UTC"
}

resource "aws_cloudwatch_event_target" "iv_calculation_target" {
  rule      = aws_cloudwatch_event_rule.iv_calculation_daily.name
  target_id = "ivCalcLambda"
  arn       = aws_lambda_function.iv_calc.arn
}

resource "aws_lambda_permission" "allow_eventbridge_iv" {
  statement_id  = "AllowExecutionFromEventBridgeIV"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.iv_calc.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.iv_calculation_daily.arn
}