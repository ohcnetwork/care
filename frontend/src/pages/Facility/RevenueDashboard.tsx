import { useQuery } from "@tanstack/react-query";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

import Page from "@/components/Common/Page";

import query from "@/Utils/request/query";
import tenantApi from "@/types/parxio/tenantApi";

export default function RevenueDashboard({
  facilityId,
}: {
  facilityId: string;
}) {
  const { data } = useQuery({
    queryKey: ["facility-revenue", facilityId],
    queryFn: query(tenantApi.incentives, {
      pathParams: { facilityId },
    }),
  });

  const doctorTotal = data?.doctor_total ?? "0";
  const progressValue =
    data && data.threshold_target
      ? (data.threshold_progress / data.threshold_target) * 100
      : 0;

  return (
    <Page title="Revenue" hideTitleOnPage>
      <div className="container mx-auto max-w-4xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Revenue</h1>
          <p className="mt-1 text-sm text-gray-600">
            Real-time ABDM incentive tracking for this month.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>ABDM Earnings This Month: ₹{doctorTotal}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="mb-2 flex items-center justify-between text-sm text-gray-600">
                <span>Threshold Progress</span>
                <span>
                  {data?.threshold_progress ?? 0}/{data?.threshold_target ?? 100}{" "}
                  patients
                </span>
              </div>
              <Progress value={progressValue} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <p className="text-sm text-gray-500">Doctor Cut</p>
                <p className="text-2xl font-semibold text-gray-900">
                  ₹{doctorTotal}
                </p>
              </div>
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <p className="text-sm text-gray-500">Parxio Cut</p>
                <p className="text-2xl font-semibold text-gray-900">
                  ₹{data?.parxio_total ?? "0"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </Page>
  );
}
