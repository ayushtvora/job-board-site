-- CreateTable
CREATE TABLE "scrape_requests" (
    "id" SERIAL NOT NULL,
    "requested_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "started_at" TIMESTAMP(3),
    "finished_at" TIMESTAMP(3),
    "status" TEXT NOT NULL DEFAULT 'pending',
    "error_message" TEXT,

    CONSTRAINT "scrape_requests_pkey" PRIMARY KEY ("id")
);
