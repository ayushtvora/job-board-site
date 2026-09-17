import "dotenv/config";
import { PrismaClient } from "../src/generated/prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";

const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL });
const prisma = new PrismaClient({ adapter });

async function main() {
  const rbc = await prisma.company.upsert({
    where: { slug: "rbc" },
    update: {},
    create: { slug: "rbc", name: "RBC" },
  });

  const shopify = await prisma.company.upsert({
    where: { slug: "shopify" },
    update: {},
    create: { slug: "shopify", name: "Shopify" },
  });

  const td = await prisma.company.upsert({
    where: { slug: "td" },
    update: {},
    create: { slug: "td", name: "TD" },
  });

  const jobs = [
    // Default-visible: open, not applied, will apply.
    {
      companyId: rbc.id,
      externalId: "R-00012345",
      title: "Software Developer",
      url: "https://jobs.rbc.com/ca/en/job/R-00012345",
      location: "Toronto, ON",
      category: "Technology, Analytics & Research",
      postedDate: new Date("2026-09-15"),
      platform: "Workday",
    },
    {
      companyId: rbc.id,
      externalId: "R-00012399",
      title: "Data Analyst",
      url: "https://jobs.rbc.com/ca/en/job/R-00012399",
      location: "Toronto, ON",
      category: "Technology, Analytics & Research",
      postedDate: new Date("2026-09-10"),
      platform: "Workday",
    },
    {
      companyId: shopify.id,
      externalId: "SHOP-4821",
      title: "Backend Engineer",
      url: "https://www.shopify.com/careers/SHOP-4821",
      location: "Remote",
      category: "Engineering",
      postedDate: new Date("2026-09-16"),
      platform: "Greenhouse",
    },
    // No posted date exposed by the source site.
    {
      companyId: shopify.id,
      externalId: "SHOP-4790",
      title: "Platform Engineer",
      url: "https://www.shopify.com/careers/SHOP-4790",
      location: "Remote",
      category: "Engineering",
      postedDate: null,
      platform: "Greenhouse",
    },
    // Already applied -> hidden by default filter, visible via "show hidden".
    {
      companyId: td.id,
      externalId: "TD-77213",
      title: "Software Engineer I",
      url: "https://jobs.td.com/en-CA/jobs/TD-77213",
      location: "Toronto, ON",
      category: "Technology",
      postedDate: new Date("2026-08-20"),
      platform: "Eightfold",
      applied: true,
      appliedAt: new Date("2026-08-22"),
    },
    // Expired (is_active = false) -> hidden by default filter, but kept
    // because it was applied to.
    {
      companyId: td.id,
      externalId: "TD-77050",
      title: "QA Engineer",
      url: "https://jobs.td.com/en-CA/jobs/TD-77050",
      location: "Toronto, ON",
      category: "Technology",
      postedDate: new Date("2026-07-01"),
      platform: "Eightfold",
      applied: true,
      appliedAt: new Date("2026-07-03"),
      isActive: false,
    },
    // Decided not to apply -> out of scope for both default and hidden views.
    {
      companyId: rbc.id,
      externalId: "R-00011980",
      title: "Java Developer",
      url: "https://jobs.rbc.com/ca/en/job/R-00011980",
      location: "Mississauga, ON",
      category: "Technology, Analytics & Research",
      postedDate: new Date("2026-09-05"),
      platform: "Workday",
      willApply: false,
    },
  ];

  for (const job of jobs) {
    await prisma.job.upsert({
      where: {
        companyId_externalId: {
          companyId: job.companyId,
          externalId: job.externalId,
        },
      },
      update: {},
      create: job,
    });
  }

  console.log(`Seeded ${jobs.length} jobs across 3 companies.`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
