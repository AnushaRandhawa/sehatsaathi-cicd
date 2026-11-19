@echo off
cd /d D:\sehatsaathi
docker compose exec -T db psql -U sehat -d sehatsaathi < reset.sql
docker compose exec -T redis redis-cli flushall
pause