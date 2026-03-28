"""Script standalone para polling via cron job.

Executa um ciclo de polling sem iniciar o servidor web.
Usado pelo Render cron job (1x/dia às 4h BRT).
"""

import sys
import logging

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from app.database import Base, engine

# Criar tabelas se não existirem
Base.metadata.create_all(bind=engine)

from app.services.polling_service import run_polling_cycle

if __name__ == "__main__":
    logging.info("Polling cycle started (cron job)")
    run_polling_cycle()
    logging.info("Polling cycle finished")
