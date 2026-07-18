import { useQuery } from "@tanstack/react-query";
import { apiDetail, client } from "../../../api/client";
import type { DistrictRead } from "../../../api/types";
import { ErrorBanner } from "../../../components/ErrorBanner";

export function DistrictsPage() {
  const districtsQuery = useQuery({
    queryKey: ["districts"],
    queryFn: async (): Promise<DistrictRead[]> => {
      const { data, error } = await client.GET("/districts/");
      if (error) throw new Error(apiDetail(error));
      return data;
    },
  });

  return (
    <div>
      <h1 className="mb-3 text-xl font-bold">Districts</h1>
      <ErrorBanner message={districtsQuery.error ? districtsQuery.error.message : null} />
      {districtsQuery.data?.length === 0 && (
        <p className="text-sm text-gray-500">No districts yet.</p>
      )}
      {districtsQuery.data && districtsQuery.data.length > 0 && (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-gray-300 text-left">
              <th className="py-1">Name</th>
              <th className="py-1">Abbreviation</th>
            </tr>
          </thead>
          <tbody>
            {districtsQuery.data.map((d) => (
              <tr key={d.id} className="border-b border-gray-200">
                <td className="py-1">{d.name}</td>
                <td className="py-1">{d.abbreviation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
